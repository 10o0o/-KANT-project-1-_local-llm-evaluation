import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from llm_eval.shared.processes import workload


@unittest.skipUnless(os.environ.get("LLM_EVAL_RUN_PROCESS_TESTS") == "1", "opt-in synthetic processes")
class RealWorkloadTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

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
from llm_eval.shared.processes import workload
for kind in ('warmup', 'local'):
    with workload(Path(sys.argv[1]), kind, allow_inherited=True) as lease:
        assert lease.borrowed
    os.fstat(lease.fd)
print('borrowed')
"""
        contend = """
import sys
from pathlib import Path
from llm_eval.shared.processes import workload
try:
    with workload(Path(sys.argv[1]), 'cloud'):
        pass
except RuntimeError:
    print('blocked')
else:
    print('acquired')
"""
        with workload(self.root, "queue") as parent:
            child = self.child(borrow, parent)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout.strip(), "borrowed")
            for _ in range(2):
                contender = self.child(contend)
                self.assertEqual(contender.returncode, 0, contender.stderr)
                self.assertEqual(contender.stdout.strip(), "blocked")
        released = self.child(contend)
        self.assertEqual(released.returncode, 0, released.stderr)
        self.assertEqual(released.stdout.strip(), "acquired")

    def test_wrong_description_and_wrong_inode_are_rejected(self):
        code = """
import os, sys
from pathlib import Path
from llm_eval.shared.processes import workload, workload_lock_path
root = Path(sys.argv[1])
for path in (workload_lock_path(root), root / 'other.lock'):
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    os.environ['LLM_EVAL_WORKLOAD_LOCK_FD'] = str(fd)
    try:
        with workload(root, 'local', allow_inherited=True):
            raise AssertionError('accepted invalid descriptor')
    except RuntimeError:
        pass
    finally:
        os.close(fd)
print('rejected')
"""
        with workload(self.root, "queue"):
            child = self.child(code)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout.strip(), "rejected")

    def test_simultaneous_contenders_have_one_owner(self):
        code = """
import sys
from pathlib import Path
from llm_eval.shared.processes import workload
try:
    with workload(Path(sys.argv[1]), 'cloud'):
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
        with workload(self.root, "cloud") as lease:
            self.assertFalse(lease.borrowed)
