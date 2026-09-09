# MC Battle Local MVP

スマホでビートに合わせてラップし、4小節ごとにローカルAIがアンサーを返す Expo + FastAPI のMVPです。採点、勝敗、ログイン、クラウド利用はありません。

## 実装済みのコア体験

- Home → Settings → Battle → Finish の画面遷移
- 3種類のビートメタデータ（90 / 100 / 120 BPM）と、4/4の正確な小節時間計算
- `8 bars × 4 rounds` と `16 bars × 2 rounds`、USER / AI先攻、4つのAIラッパー人格
- 4小節録音を区切り、次の4小節の録音中に前チャンクを `STT → LLM → TTS` 処理するパイプライン
- faster-whisper による日本語・英語混在のローカル文字起こし
- Ollamaに4本固定のJSONを要求し、壊れたJSONは一度再生成後に4本の安全なフォールバックへ切替
- VOICEVOX（既定）または pyttsx3 によるローカルTTS。各barをWAV化し、BPMの1小節に近づけてから端末で小節頭再生
- STT・AI歌詞は画面に表示せず、バックエンドログだけで確認
- FastAPI接続、マイク権限、Whisper、Ollama、TTSの失敗を画面／ログの双方で扱う

## 構成

```text
.
├─ App.tsx                         # 最小の画面遷移
├─ src/
│  ├─ screens/                     # Home / Settings / Battle / Finish
│  ├─ features/battle/
│  │  ├─ battleEngine.ts            # ターン、round、4小節chunkの純粋な遷移
│  │  ├─ timing.ts                  # BPM・4/4・bar/chunk時間
│  │  ├─ useBattleController.ts     # 録音、並列パイプライン、AI再生
│  │  └─ beats.ts                   # ビートメタデータ
│  └─ services/                    # FastAPI通信・TTS再生
├─ assets/beats/                   # ライセンス済みビートを後から置く場所
└─ backend/app/
   ├─ main.py                      # /health, /process-chunk と静的WAV配信
   ├─ services/stt.py              # faster-whisper
   ├─ services/llm.py              # Ollama JSON生成・検証
   ├─ services/tts.py              # VOICEVOX / pyttsx3
   ├─ services/audio.py            # 1小節への速度・無音調整
   └─ prompts/rappers.py           # 4人格と共通プロンプト
```

## 4小節パイプライン

```text
USER 1–4 録音 ──送信──> STT → Ollama → TTS ──┐
USER 5–8 録音 ──送信──> STT → Ollama → TTS ──┼─> AI 1–4 → AI 5–8
                                               │
                                       4 barごとに次の応答を先読み
```

FastAPIの `POST /process-chunk` は音声（AI先攻時はなし）、直近履歴、人格、BPMを受け取ります。応答には文字起こし、必ず4本のbars、4本のTTS音声URLを返します。フロントエンドはユーザーの録音終了を待つだけでHTTP処理自体は待たないため、次の4小節中に処理が進みます。

AI先攻では最初のAI4小節をオープニングとして生成し、以降のUSERターンへの返答は次のAIターンで行います。これはAI先攻でも会話の順序を崩さないためです。

## フロントエンドを起動する

Node.js LTSを用意してから、プロジェクトルートで実行します。

```powershell
Copy-Item .env.example .env
# .env 内の 192.168.x.x を、このPCのIPv4アドレスに変更
npm install
npx expo start
```

同じWi-Fi上のiOS/Android端末で Expo Go からQRコードを読み取り、マイクを許可してください。`expo-audio` はExpo Goで録音・再生できる構成です。バックグラウンド録音やロック画面での長時間再生を追加する場合だけ、`app.json` のプラグイン設定を反映する Expo Development Build が必要です。

`EXPO_PUBLIC_API_BASE_URL` はアプリを起動し直して読み込みます。例えばPCのIPv4が `192.168.1.25` なら次のようにします。

```dotenv
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.25:8000
```

## バックエンドを起動する

Python 3.10以上を想定しています。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# OLLAMA_MODEL を実際に取得したローカルモデル名へ変更
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

別のPowerShellで、PC自身から疎通を確認します。

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Windows Defender Firewall が尋ねたら、**プライベートネットワーク**上でポート8000への受信を許可してください。公開ネットワークやインターネットへ公開しないでください。

## Ollama（ローカルLLM）

1. [Ollama for Windows](https://docs.ollama.com/windows) をインストールします。
2. 日本語を扱える、PCに収まるモデルを選んで取得します。モデル名はここでは固定しません。

   ```powershell
   ollama pull <モデル名>
   ollama list
   ```

3. `backend/.env` の `OLLAMA_MODEL=<モデル名>` を `ollama list` に出た名前と完全に一致させます。

Windows版は通常バックグラウンドでローカルAPI（`127.0.0.1:11434`）を提供します。必要なら `ollama serve` を実行してください。

## Whisper（ローカルSTT）

この実装は **faster-whisper** を選択しています。CPUでのMVP速度を優先して既定を多言語 `base` + `int8` にしています。精度が必要なら `backend/.env` の `WHISPER_MODEL=small` に変更してください（初回ロード時にモデルをローカルへ取得します）。faster-whisper はPyAV経由で音声をデコードするため、通常の基本利用では別途ffmpegを入れる必要はありません。

GPUを使う場合は、faster-whisper / CTranslate2 が要求するCUDA・cuDNNの組み合わせを確認して `WHISPER_DEVICE=cuda` と適切な `WHISPER_COMPUTE_TYPE` に変更してください。

## TTS（ローカル）

既定は日本語品質を優先した **VOICEVOX Engine** です。Docker Desktopがある場合、次でPCローカルに起動できます。

```powershell
docker run --rm -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-latest
```

FastAPIとVOICEVOXは同じPC内通信だけなので、VOICEVOXのポートをLANへ開ける必要はありません。`VOICEVOX_SPEAKER_ID` は利用する音声ライブラリに合わせて変更できます。VOICEVOXを利用する際は、音声ライブラリごとの利用規約・クレジット表記要件を確認してください。

VOICEVOXを動かせない場合は `TTS_ENGINE=pyttsx3` に切り替えられますが、日本語の自然さはOSに入っている音声に依存します。

## ビートを追加する

リポジトリにはライセンス不明な音源を含めていません。MVPは音源未配置でもBPMの視覚カウントでタイミングを保ち、録音・パイプライン・AI音声再生を検証できます。

ライセンス済みのループ可能な音源を `assets/beats/` に置き、`src/features/battle/beats.ts` の該当 `audioUri` に端末で再生できるファイルURIを割り当てれば、バトル開始時から低音量でループします。将来のファイルインポート機能も同じ `audioUri` を設定するだけで接続できます。バンドル済みアセットを使う場合は、Expoの`require()`で得たアセット参照に `Beat` の型を拡張して設定してください。

## 確認方法

```powershell
# フロントエンド（依存インストール後）
npm run typecheck

# バックエンド
cd backend
.\.venv\Scripts\python -m compileall app
```

実機テストの前に、`/health`、Ollama、VOICEVOXがそれぞれ起動していることを確認してください。

## 既知の制約・未実装

- リポジトリにビート音源は入っていないため、初期状態ではビートの**実音再生**ではなくBPMカウントです。音源を追加するとループ再生する設計です。
- ストリーミングSTTは未実装です。安定性を優先し、4小節を録音完了してから送信します。
- TTSはラップ専用ではありません。速度は0.8〜1.35倍までの穏やかな補正に留め、極端に長い生成文はプロンプトで抑制します。
- ローカルモデル性能・PC性能・Wi-Fi遅延によって、AIが次の小節頭に間に合わない場合があります。その場合はクラッシュせず「AI PREPARING」のまま待ちます。
- BGMをスピーカーで出すとマイクに混ざるため、実際の練習ではイヤホン／ヘッドホンを推奨します。
- 音声ファイルと録音の永続保存、採点、勝敗、字幕、履歴、オンライン対戦、ユーザーのビート追加UIは意図的に実装していません。
