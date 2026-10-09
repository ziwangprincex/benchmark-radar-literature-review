"""文献综述：逐篇抽卡 → 分类 → 写综述 → 按批注改稿。

- prompts/   三步各自的写作说明（cards / taxonomy / review），改它们就改综述的写法
- corpus.py  资料：某领域的论文摘要
- check.py   防编造核对：编号存在、原话对得上（不打分）
- llm.py     OpenAI 兼容接口
- pipeline.py 三步流程、后台运行、读取结果
"""
