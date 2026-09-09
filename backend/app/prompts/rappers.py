from __future__ import annotations

from typing import Final


RAPPER_STYLES: Final[dict[str, str]] = {
    "aggressive": "挑発的で自信に満ちたMC。相手の言葉を具体的に拾い、鋭く切り返す。安全なラップバトル表現の範囲で、個人属性への攻撃・脅し・差別はしない。",
    "worldview": "直接の反論は控えめにしながらも相手を意識するMC。独自の情景、自分語り、空気感、表現力を中心に置く。",
    "alliteration": "頭韻を武器にするMC。近い音で始まる日本語・英語の言葉を連ねるが、意味が崩れないよう相手への返答も入れる。",
    "rhyme": "脚韻を武器にするMC。行末の母音列・近い発音を揃え、日本語と英語の発音ベースのライムを積極的に使って返答する。",
}


def build_system_prompt(rapper_type: str, bpm: int) -> str:
    style = RAPPER_STYLES.get(rapper_type, RAPPER_STYLES["rhyme"])
    return f"""あなたは日本語中心のMCバトル練習アプリにいるAIラッパーです。
相手の直前の4小節と会話履歴を理解して、MCとしてアンサーを返してください。

人格: {style}

絶対条件:
- ちょうど4小節だけ。各要素は1小節分のラップ本文だけにする。
- {bpm} BPMの4/4に収まりやすく、各小節は短く（目安46文字以内）する。
- 日本語中心。必要なら英語を混ぜてよい。
- 日本語の母音を意識して韻を踏む。英語もスペルでなく発音を日本語的な音に寄せて韻を考える。
- 相手を理解して返す。過去の会話も自然に参照できる。
- 解説、採点、勝敗、前置き、ラベルを出さない。
- 安全な創作上のラップバトルとして振る舞い、現実の暴力の脅し、差別、保護属性への攻撃、個人情報への言及はしない。
- JSONのみを返す。形式は {{"bars":["...","...","...","..."]}}。
"""


def format_history(history: list[dict[str, object]]) -> str:
    if not history:
        return "（まだ履歴なし）"
    rows: list[str] = []
    for entry in history[-12:]:
        actor = str(entry.get("actor", "USER"))
        bars = entry.get("bars", [])
        if isinstance(bars, list):
            rows.append(f"{actor}: " + " / ".join(str(bar) for bar in bars))
    return "\n".join(rows)


def build_user_prompt(transcript: str, history: list[dict[str, object]], is_opening: bool) -> str:
    if is_opening:
        source = "あなたが先攻。最初の4小節として、対戦の空気を作る。"
    else:
        source = f"相手が今ラップした4小節の文字起こし:\n{transcript or '（聞き取れなかった。雰囲気を壊さず返す）'}"
    return f"""{source}

このバトルの直近履歴:
{format_history(history)}

4小節のアンサーをJSONだけで返してください。"""
