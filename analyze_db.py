import sqlite3
import numpy as np

DB_PATH = "./data/forceteller_test.db"

def analyze_patterns():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 모든 결과 조회 (오행 점수 중심)
    cursor.execute("""
        SELECT 
            ft_wood, ft_fire, ft_earth, ft_metal, ft_water,
            ft_wood_hap, ft_fire_hap, ft_earth_hap, ft_metal_hap, ft_water_hap,
            ft_wood_johoo, ft_fire_johoo, ft_earth_johoo, ft_metal_johoo, ft_water_johoo,
            ft_wood_adj, ft_fire_adj, ft_earth_adj, ft_metal_adj, ft_water_adj,
            
            my_wood, my_fire, my_earth, my_metal, my_water,
            my_wood_hap, my_fire_hap, my_earth_hap, my_metal_hap, my_water_hap,
            my_wood_johoo, my_fire_johoo, my_earth_johoo, my_metal_johoo, my_water_johoo,
            my_wood_adj, my_fire_adj, my_earth_adj, my_metal_adj, my_water_adj
        FROM test_results
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("데이터가 없습니다.")
        return

    # 분석용 리스트
    ft_base_list, ft_hap_list, ft_johoo_list, ft_adj_list = [], [], [], []
    my_base_list, my_hap_list, my_johoo_list, my_adj_list = [], [], [], []

    for row in rows:
        # FT
        ft_base = [row['ft_wood'], row['ft_fire'], row['ft_earth'], row['ft_metal'], row['ft_water']]
        ft_hap = [row['ft_wood_hap'], row['ft_fire_hap'], row['ft_earth_hap'], row['ft_metal_hap'], row['ft_water_hap']]
        ft_johoo = [row['ft_wood_johoo'], row['ft_fire_johoo'], row['ft_earth_johoo'], row['ft_metal_johoo'], row['ft_water_johoo']]
        ft_adj = [row['ft_wood_adj'], row['ft_fire_adj'], row['ft_earth_adj'], row['ft_metal_adj'], row['ft_water_adj']]

        # MY
        my_base = [row['my_wood'], row['my_fire'], row['my_earth'], row['my_metal'], row['my_water']]
        my_hap = [row['my_wood_hap'], row['my_fire_hap'], row['my_earth_hap'], row['my_metal_hap'], row['my_water_hap']]
        my_johoo = [row['my_wood_johoo'], row['my_fire_johoo'], row['my_earth_johoo'], row['my_metal_johoo'], row['my_water_johoo']]
        my_adj = [row['my_wood_adj'], row['my_fire_adj'], row['my_earth_adj'], row['my_metal_adj'], row['my_water_adj']]
        
        # 0 처리 (None 방지)
        ft_base = [x if x else 0.0 for x in ft_base]
        ft_hap = [x if x else 0.0 for x in ft_hap]
        ft_johoo = [x if x else 0.0 for x in ft_johoo]
        ft_adj = [x if x else 0.0 for x in ft_adj]
        
        my_base = [x if x else 0.0 for x in my_base]
        my_hap = [x if x else 0.0 for x in my_hap]
        my_johoo = [x if x else 0.0 for x in my_johoo]
        my_adj = [x if x else 0.0 for x in my_adj]

        ft_base_list.append(ft_base)
        ft_hap_list.append(ft_hap)
        ft_johoo_list.append(ft_johoo)
        ft_adj_list.append(ft_adj)
        
        my_base_list.append(my_base)
        my_hap_list.append(my_hap)
        my_johoo_list.append(my_johoo)
        my_adj_list.append(my_adj)

    # 평균 차이 분석
    # 1. 합(Hap) 효과: Hap - Base
    ft_hap_effect = np.array(ft_hap_list) - np.array(ft_base_list)
    my_hap_effect = np.array(my_hap_list) - np.array(my_base_list)
    
    # 2. 조후(Johoo) 효과: Johoo - Base
    ft_johoo_effect = np.array(ft_johoo_list) - np.array(ft_base_list)
    my_johoo_effect = np.array(my_johoo_list) - np.array(my_base_list)

    # 3. 보정(Adj) 효과: Adj - Base
    ft_adj_effect = np.array(ft_adj_list) - np.array(ft_base_list)
    my_adj_effect = np.array(my_adj_list) - np.array(my_base_list)
    
    print("=== 분석 결과 (평균 변화량) ===")
    print(f"분석 데이터 수: {len(rows)}건")
    print("\n[합(Hap) 적용 시 변화 평균 (오행 순서: 목, 화, 토, 금, 수)]")
    print(f"FT: {np.mean(np.abs(ft_hap_effect), axis=0)}")
    print(f"MY: {np.mean(np.abs(my_hap_effect), axis=0)}")
    
    print("\n[조후(Johoo) 적용 시 변화 평균]")
    print(f"FT: {np.mean(np.abs(ft_johoo_effect), axis=0)}")
    print(f"MY: {np.mean(np.abs(my_johoo_effect), axis=0)}")
    
    print("\n[전체 보정(Adj) 적용 시 변화 평균]")
    print(f"FT: {np.mean(np.abs(ft_adj_effect), axis=0)}")
    print(f"MY: {np.mean(np.abs(my_adj_effect), axis=0)}")
    
    # 변화가 있는 케이스 비율
    ft_hap_changed = np.sum(np.any(ft_hap_effect != 0, axis=1))
    ft_johoo_changed = np.sum(np.any(ft_johoo_effect != 0, axis=1))
    
    print(f"\n[변화 발생 빈도]")
    print(f"FT 합 적용 시 변화 발생: {ft_hap_changed}/{len(rows)} ({ft_hap_changed/len(rows)*100:.1f}%)")
    print(f"FT 조후 적용 시 변화 발생: {ft_johoo_changed}/{len(rows)} ({ft_johoo_changed/len(rows)*100:.1f}%)")
    
    # 변화가 감지된 케이스 번호 출력
    print("\n[변화가 감지된 케이스 번호]")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT test_no, ft_wood, ft_wood_hap, ft_wood_johoo FROM test_results")
    for r in cursor.fetchall():
        no = r[0]
        base = r[1]
        hap = r[2]
        johoo = r[3]
        if base != hap:
            print(f"  - Case #{no}: 합 변화 감지")
        if base != johoo:
            print(f"  - Case #{no}: 조후 변화 감지")
    conn.close()

if __name__ == "__main__":
    analyze_patterns()
