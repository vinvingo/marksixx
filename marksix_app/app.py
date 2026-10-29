import streamlit as st
import pandas as pd
import requests
import io
import random
from collections import Counter

# 頁面基本設定
st.set_page_config(
    page_title="香港六合彩智能分析與選號系統",
    page_icon="🎲",
    layout="wide"
)

# 遠端數據源與本地快取設定
CSV_FILENAME = "marksix_history.csv"
REMOTE_URL = "https://raw.githubusercontent.com/icelam/mark-six-data-visualization/main/data/marksix.csv"

@st.cache_data(ttl=3600)
def load_data(force_update=False):
    """載入或更新歷史開獎數據"""
    df = None
    if not force_update:
        try:
            df = pd.read_csv(CSV_FILENAME)
        except Exception:
            pass
    
    if df is None:
        try:
            response = requests.get(REMOTE_URL, timeout=10)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))
            df.to_csv(CSV_FILENAME, index=False)
        except Exception as e:
            st.error(f"無法從遠端載入數據，請檢查網絡連線：{e}")
            try:
                df = pd.read_csv(CSV_FILENAME)
            except Exception:
                df = None
    return df

def get_clean_draws(df):
    """清洗並取得標準化的歷史開獎清單"""
    if df is None:
        return []
    possible_cols = [col for col in df.columns if any(k in col.lower() for k in ['n', 'num', 'ball', 'draw']) or col.isdigit()]
    if len(possible_cols) >= 6:
        number_cols = possible_cols[:6]
    else:
        number_cols = df.columns[-6:]
        
    draws = []
    for idx, row in df.iterrows():
        try:
            draw = [int(row[col]) for col in number_cols]
            if len(draw) == 6 and all(1 <= n <= 49 for n in draw):
                # 嘗試取得期數或日期（若欄位存在）
                draws.append({
                    "index": idx + 1,
                    "numbers": sorted(draw)
                })
        except (ValueError, TypeError):
            continue
    return draws

def is_balanced_combination(numbers):
    """智能過濾條件檢查"""
    odd_count = sum(1 for n in numbers if n % 2 != 0)
    total_sum = sum(numbers)
    if odd_count < 2 or odd_count > 4: return False
    if total_sum < 100 or total_sum > 200: return False
    for i in range(len(numbers) - 2):
        if numbers[i+1] == numbers[i] + 1 and numbers[i+2] == numbers[i] + 2:
            return False
    return True

# --- 網頁介面佈局 ---
st.title("🎲 香港六合彩數據分析與智能選號系統")
st.markdown("結合真實歷史數據與統計學策略，支援即時分析、多維度選號與歷史對獎模擬。")

# 側邊欄控制項
st.sidebar.header("⚙️ 設定與數據同步")
if st.sidebar.button("🔄 強制更新遠端數據"):
    st.cache_data.clear()
    df = load_data(force_update=True)
    st.sidebar.success("歷史數據已成功更新！")
else:
    df = load_data(force_update=False)

draws_data = get_clean_draws(df)

if not draws_data:
    st.warning("⚠️ 目前找不到歷史開獎數據，請確認網絡連線或本地 CSV 檔案是否存在。")
else:
    # 提取純數字列表用於統計
    all_draw_lists = [d["numbers"] for d in draws_data]
    all_nums = [num for draw in all_draw_lists for num in draw]
    freq = Counter(all_nums)
    full_freq = {i: freq.get(i, 0) for i in range(1, 50)}
    sorted_freq = sorted(full_freq.items(), key=lambda x: x[1], reverse=True)
    hot_pool = [item[0] for item in sorted_freq[:15]]
    cold_pool = [item[0] for item in sorted_freq[-15:]]

    # 頁籤切換（新增第三個頁籤）
    tab1, tab2, tab3 = st.tabs(["📊 歷史數據與冷熱分析", "🎯 策略選號產生器", "🔍 歷史對獎檢查器"])

    with tab1:
        st.subheader("📈 歷史開獎摘要")
        col1, col2, col3 = st.columns(3)
        col1.metric("總記錄期數", f"{len(draws_data)} 期")
        col2.metric("最近一期號碼", f"{draws_data[-1]['numbers']}")
        col3.metric("最近一期記錄", f"第 {draws_data[-1]['index']} 筆")

        st.markdown("---")
        st.subheader("🔥 1 至 49 號出現頻率長條圖")
        freq_df = pd.DataFrame(list(full_freq.items()), columns=["號碼", "出現次數"]).sort_values("號碼")
        st.bar_chart(freq_df.set_index("號碼"))

        col_hot, col_cold = st.columns(2)
        with col_hot:
            st.markdown("### 🔥 熱門號碼 Top 10 (出現頻率最高)")
            hot_df = pd.DataFrame(sorted_freq[:10], columns=["號碼", "出現次數"])
            st.dataframe(hot_df, hide_index=True, use_container_width=True)
        with col_cold:
            st.markdown("### ❄️ 冷門號碼 Bottom 10 (出現頻率最低)")
            cold_df = pd.DataFrame(sorted_freq[-10:], columns=["號碼", "出現次數"])
            st.dataframe(cold_df, hide_index=True, use_container_width=True)

    with tab2:
        st.subheader("🎯 智能策略選號器")
        strategy = st.selectbox(
            "選擇選號策略模型",
            [
                "冷熱平衡策略 (Balanced: 熱2 + 冷2 + 隨機2)",
                "熱門追蹤策略 (Hot: 偏好近期高頻號碼)",
                "冷門回歸策略 (Cold: 偏好長時間未出號碼)",
                "智能過濾隨機 (Smart Filter: 避開極端單雙與連號)"
            ]
        )
        count = st.slider("產生注數", min_value=1, max_value=10, value=5)

        if st.button("🚀 開始產生選號", type="primary"):
            results = []
            attempts = 0
            while len(results) < count and attempts < 1000:
                attempts += 1
                if "冷熱平衡" in strategy:
                    h = random.sample(hot_pool, 2)
                    c = random.sample(cold_pool, 2)
                    rem = [i for i in range(1, 50) if i not in h and i not in c]
                    sel = sorted(h + c + random.sample(rem, 2))
                elif "熱門追蹤" in strategy:
                    sel = sorted(random.sample(hot_pool, min(4, len(hot_pool))) + random.sample([i for i in range(1, 50) if i not in hot_pool], 2))
                elif "冷門回歸" in strategy:
                    sel = sorted(random.sample(cold_pool, min(4, len(cold_pool))) + random.sample([i for i in range(1, 50) if i not in cold_pool], 2))
                else:  # 智能過濾隨機
                    cand = sorted(random.sample(range(1, 50), 6))
                    if is_balanced_combination(cand):
                        results.append(cand)
                    continue
                
                if sel not in results:
                    results.append(sel)

            st.success(f"成功為你產生以下 {len(results)} 注號碼：")
            for idx, res in enumerate(results, 1):
                st.info(f"**第 {idx} 注：** `{res}` (號碼總和: {sum(res)})")

    with tab3:
        st.subheader("🔍 歷史對獎檢查器")
        st.markdown("輸入你的 6 個選號（1 至 49 之間），系統將自動掃描全部歷史開獎記錄，檢查這組號碼在歷史上中過幾次獎。")

        # 使用 6 個欄位讓使用者輸入 6 個號碼
        cols = st.columns(6)
        user_input_nums = []
        default_vals = [3, 12, 24, 35, 42, 48]
        
        for i in range(6):
            val = cols[i].number_input(f"第 {i+1} 個號碼", min_value=1, max_value=49, value=default_vals[i], key=f"num_{i}")
            user_input_nums.append(int(val))

        user_selection = sorted(user_input_nums)

        # 檢查是否有重複號碼
        if len(set(user_selection)) < 6:
            st.error("⚠️ 號碼不能有重複！請確保 6 個號碼各不相同。")
        else:
            st.write(fox := f"你當前選擇的對獎號碼：**`{user_selection}`**")

            if st.button("🔎 開始比對歷史開獎", type="primary"):
                match_results = {6: [], 5: [], 4: [], 3: []}

                for draw_item in draws_data:
                    d_nums = draw_item["numbers"]
                    # 計算交集（中了幾個號碼）
                    common = set(user_selection).intersection(set(d_nums))
                    hit_count = len(common)
                    if hit_count >= 3:
                        match_results[hit_count].append({
                            "index": draw_item["index"],
                            "matched_numbers": sorted(list(common)),
                            "draw_numbers": d_nums
                        })

                # 顯示對獎結果統計
                st.markdown("---")
                st.subheader("📊 對獎統計摘要")
                
                m6 = len(match_results[6])
                m5 = len(match_results[5])
                m4 = len(match_results[4])
                m3 = len(match_results[3])

                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                col_r1.metric("6 個全中 (頭獎級)", f"{m6} 次")
                col_r2.metric("5 個字", f"{m5} 次")
                col_r3.metric("4 個字", f"{m4} 次")
                col_r4.metric("3 個字", f"{m3} 次")

                # 細節清單展示
                if m6 > 0 or m5 > 0 or m4 > 0:
                    st.markdown("### 🏆 中獎記錄詳情（3個字或以上）")
                    for prize_tier in [6, 5, 4, 3]:
                        records = match_results[prize_tier]
                        if records:
                            st.markdown(f"#### 🔹 中 {prize_tier} 個號碼 ({len(records)} 次)")
                            for rec in records:
                                st.write(f"- **記錄編號 #{rec['index']}** | 開獎號碼: `{rec['draw_numbers']}` | 命中號碼: `{rec['matched_numbers']}`")
                else:
                    st.info("💡 在現有的歷史數據中，這組號碼最高只中過少於 3 個字（或未曾中過 3 個字以上）。")