import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from llm_eval.shared.workloads import workload


@unittest.skipUnless(os.environ.get("LLM_EVAL_RUN_PROCESS_TESTS") == "1", "opt-in synthetic processes")
class RealWorkloadTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.proc = self.root / "proc"
        self.proc.mkdir()

    def child(self, code, lease=None, extra_env=None):
        env = dict(os.environ)
        env.pop("LLM_EVAL_WORKLOAD_LOCK_FD", None)
        if lease:
            env = lease.child_env(env)
        env.update(extra_env or {})
        return subprocess.run(
            [sys.executable, "-c", code, str(self.root)],
            env=env, pass_fds=lease.child_pass_fds() if lease else (),
            capture_output=True, text=True, timeout=5,
        )

    def test_queue_children_borrow_without_releasing_parent(self):
        borrow = """
import os, sys
from pathlib import Path
from llm_eval.shared.workloads import workload
root = Path(sys.argv[1])
for kind in ('warmup', 'local'):
    with workload(root, kind, allow_inherited=True, proc_root=root / 'proc') as lease:
        assert lease.borrowed
    os.fstat(lease.fd)
print('borrowed')
"""
        cloud = """
import sys
from pathlib import Path
from llm_eval.shared.workloads import workload
try:
    root = Path(sys.argv[1])
    with workload(root, 'cloud', proc_root=root / 'proc'):
        pass
except RuntimeError:
    print('blocked')
else:
    print('acquired')
"""
        with workload(self.root, "queue", proc_root=self.proc) as parent:
            child = self.child(borrow, parent)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout.strip(), "borrowed")
            for _ in range(2):
                contender = self.child(cloud)
                self.assertEqual(contender.returncode, 0, contender.stderr)
                self.assertEqual(contender.stdout.strip(), "acquired")
            judge = self.child(cloud.replace("'cloud'", "'judge'"))
            self.assertEqual(judge.returncode, 0, judge.stderr)
            self.assertEqual(judge.stdout.strip(), "blocked")
        released = self.child(cloud)
        self.assertEqual(released.returncode, 0, released.stderr)
        self.assertEqual(released.stdout.strip(), "acquired")

    def test_local_and_cloud_are_symmetric_but_each_blocks_judge(self):
        template = """
import sys
from pathlib import Path
from llm_eval.shared.workloads import workload
try:
    root = Path(sys.argv[1])
    with workload(root, {kind!r}, proc_root=root / 'proc'):
        pass
except RuntimeError:
    print('blocked')
else:
    print('acquired')
"""
        for parent_kind, peer_kind in (("local", "cloud"), ("cloud", "local")):
            with self.subTest(parent=parent_kind):
                with workload(self.root, parent_kind, proc_root=self.proc):
                    peer = self.child(template.format(kind=peer_kind))
                    judge = self.child(template.format(kind="judge"))
                self.assertEqual(peer.returncode, 0, peer.stderr)
                self.assertEqual(peer.stdout.strip(), "acquired")
                self.assertEqual(judge.returncode, 0, judge.stderr)
                self.assertEqual(judge.stdout.strip(), "blocked")

    def test_judge_holder_blocks_both_lanes_then_releases_them(self):
        template = """
import sys
from pathlib import Path
from llm_eval.shared.workloads import workload
root = Path(sys.argv[1])
try:
    with workload(root, {kind!r}, proc_root=root / 'proc'):
        pass
except RuntimeError:
    print('blocked')
else:
    print('acquired')
"""
        with workload(self.root, "judge", proc_root=self.proc):
            blocked = [
                self.child(template.format(kind=kind))
                for kind in ("local", "cloud")
            ]
        released = [
            self.child(template.format(kind=kind)) for kind in ("local", "cloud")
        ]

        self.assertEqual([item.stdout.strip() for item in blocked], ["blocked"] * 2)
        self.assertEqual([item.stdout.strip() for item in released], ["acquired"] * 2)
        self.assertTrue(all(item.returncode == 0 for item in blocked + released))

    def test_wrong_description_and_wrong_inode_are_rejected(self):
        code = """
import os, sys
from pathlib import Path
from llm_eval.shared.workloads import (
    cloud_workload_lock_path,
    workload,
    workload_lock_path,
)
root = Path(sys.argv[1])
for path in (
    workload_lock_path(root), cloud_workload_lock_path(root), root / 'other.lock'
):
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    os.environ['LLM_EVAL_WORKLOAD_LOCK_FD'] = str(fd)
    try:
        with workload(
            root, 'local', allow_inherited=True, proc_root=root / 'proc'
        ):
            raise AssertionError('accepted invalid descriptor')
    except RuntimeError:
        pass
    finally:
        os.close(fd)
print('rejected')
"""
        with workload(self.root, "queue", proc_root=self.proc):
            child = self.child(code)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout.strip(), "rejected")

    def test_simultaneous_contenders_have_one_owner(self):
        code = """
import sys
from pathlib import Path
from llm_eval.shared.workloads import workload
try:
    root = Path(sys.argv[1])
    with workload(root, 'cloud', proc_root=root / 'proc'):
        print('owner', flush=True)
        sys.stdin.readline()
except RuntimeError:
    print('blocked', flush=True)
"""
        children = []
        try:
            for _ in range(2):
                children.append(subprocess.Popen(
                    [sys.executable, "-c", code, str(self.root)],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True,
                ))
            import selectors
            observed = []
            with selectors.DefaultSelector() as selector:
                for child in children:
                    selector.register(child.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    ready = selector.select(timeout=5)
                    self.assertTrue(ready, "contender did not report its lock state")
                    for key, _ in ready:
                        observed.append(key.fileobj.readline().strip())
                        selector.unregister(key.fileobj)
            self.assertCountEqual(observed, ["owner", "blocked"])
        finally:
            for child in children:
                try:
                    child.communicate("\n", timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.communicate(timeout=5)
        with workload(self.root, "cloud", proc_root=self.proc) as lease:
            self.assertFalse(lease.borrowed)
