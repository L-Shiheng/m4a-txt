import streamlit as st
import pandas as pd
import math
from pydub import AudioSegment
import tempfile
import os

st.set_page_config(page_title="氮空一体机噪声分析", layout="wide")

st.title("🎧 氮空一体机噪声分析工具")
st.write("上传录音文件，系统将自动提取每秒的音量分贝值（dBFS），绘制噪声趋势图，并分析波动规律。")

# 文件上传组件
uploaded_file = st.file_uploader("请上传音频文件 (支持 .m4a, .wav, .mp3)", type=["m4a", "wav", "mp3"])

if uploaded_file is not None:
    st.info("⏳ 正在加载并处理音频，由于录音较长（约1小时），这可能需要 1-2 分钟，请耐心等待...")
    
    # 获取文件后缀名
    file_extension = uploaded_file.name.split('.')[-1]
    
    # 将上传的文件保存为临时文件，因为 pydub 需要读取文件路径
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
        
    try:
        # 1. 加载音频
        audio = AudioSegment.from_file(tmp_path)
        
        # 2. 按 1 秒 (1000毫秒) 切片
        chunk_length_ms = 1000 
        chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
        
        data = []
        # 3. 提取每秒分贝值
        for i, chunk in enumerate(chunks):
            db = chunk.dBFS
            if math.isinf(db): # 处理绝对静音
                db = -100.0  
            data.append({
                "时间 (秒)": i + 1,
                "噪声大小 (dBFS)": round(db, 2)
            })
            
        # 4. 转换为 DataFrame
        df = pd.DataFrame(data)
        
        st.success("✅ 音频处理完成！")
        
        # --- 数据可视化与分析 ---
        st.header("📊 噪声变化趋势图")
        st.write("你可以缩放图表，查看哪些时间段出现了异常的噪声波峰。")
        # 将时间设为索引，方便画图
        chart_data = df.set_index("时间 (秒)")
        st.line_chart(chart_data)
        
        st.header("📈 噪声规律诊断报告")
        col1, col2, col3, col4 = st.columns(4)
        
        max_noise = df["噪声大小 (dBFS)"].max()
        min_noise = df["噪声大小 (dBFS)"].min()
        mean_noise = df["噪声大小 (dBFS)"].mean()
        variance = df["噪声大小 (dBFS)"].var() # 方差越大，代表噪声越不稳定
        
        col1.metric("最大噪声峰值", f"{max_noise} dB")
        col2.metric("最小噪声底噪", f"{min_noise} dB")
        col3.metric("平均噪声", f"{mean_noise:.2f} dB")
        
        # 解释方差
        if variance > 20:
            stability = "⚠️ 极其不稳定 (波动剧烈)"
        elif variance > 5:
            stability = "🟡 存在一定波动"
        else:
            stability = "🟢 相对稳定"
            
        col4.metric("噪声波动程度 (方差)", f"{variance:.2f}", delta=stability, delta_color="inverse")
        
        st.write("### 🔍 诊断建议：")
        st.write(f"- 如果**每次噪声大小不同**，你可以观察上面的折线图，看看波峰是不是高低不平。")
        st.write(f"- 看看高噪声（比如接近 {max_noise} dB 的地方）是否呈现**周期性**（比如每隔 10 分钟出现一次），如果是，大概率是压缩机启停或排气电磁阀动作引起。")
        
        # 提供 CSV 下载
        st.download_button(
            label="📥 下载完整的原始噪声数据 (CSV)",
            data=df.to_csv(index=False).encode('utf-8-sig'),
            file_name="noise_data.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"❌ 处理音频时发生错误: {e}")
        st.error("提示: 确保你上传的音频文件没有损坏。")
        
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
