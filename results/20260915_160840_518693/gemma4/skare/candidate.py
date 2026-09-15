import sys

def solve():
    # 표준 입력으로부터 모든 데이터를 읽어옵니다.
    input_data = sys.stdin.read().split()
    
    if not input_data:
        return

    # 첫 번째 줄에서 n과 k를 읽습니다.
    n = int(input_data[0])
    k = int(input_data[1])
    
    # 현재 가지고 있는 종이 띠들의 길이를 저장하는 리스트입니다.
    # 초기 상태는 길이가 n인 띠 하나만 존재합니다.
    strips = [n]
    
    # 명령 정보를 처리하기 위한 인덱스 변수
    current_idx = 2
    
    for _ in int(range(k)):
        # x_i: 자를 띠의 번호 (1-indexed), l_i: 자를 위치
        x = int(input_data[current_idx])
        l = int(input_data[current_idx + 1])
        current_idx += 2
        
        # x-1 인덱스의 띠를 가져옵니다.
        target_strip_idx = x - 1
        original_length = strips[target_strip_idx]
        
        # x-1 인덱스의 띠를 l과 (original_length - l)로 교체합니다.
        # 슬라이싱을 이용하면 해당 위치의 요소를 두 개로 확장하며 교체할 수 있습니다.
        strips[target_strip_idx : target_strip_idx + 1] = [l, original_length - l]
        
    # 모든 작업이 끝난 후, set을 사용하여 중복된 길이를 제거하고 개수를 셉니다.
    distinct_lengths = set(strips)
    print(len(distinct_lengths))

if __name__ == "__main__":
    # k번의 반복을 위해 range(k)를 사용하기 위해 solve 함수 내부 로직을 조정합니다.
    # 위 코드의 for _ in int(range(k)) 부분은 오타이므로 수정된 로직으로 실행합니다.
    
    # 재작성된 실행 로직
    import sys

    def main():
        input_data = sys.stdin.read().split()
        if not input_data:
            return
        
        n = int(input_data[0])
        k = int(input_data[1])
        
        strips = [n]
        ptr = 2
        for _ in range(k):
            x = int(input_data[ptr])
            l = int(input_data[ptr+1])
            ptr += 2
            
            idx = x - 1
            old_val = strips[idx]
            # 리스트의 해당 위치를 두 개의 값으로 교체
            strips[idx:idx+1] = [l, old_val - l]
            
        print(len(set(strips)))

    main()