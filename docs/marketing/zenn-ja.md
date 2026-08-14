---
title: "Claude Code の「素晴らしいご質問です！」を消す — 自前 GPU で動く書き換えフック"
emoji: "✂️"
type: "tech"
topics: ["claudecode", "mcp", "llm", "vllm", "gcp"]
published: false
---

## 何が問題か

Claude Code の返答は、内容そのものは良いのに前置きが長い。

> 素晴らしいご質問です！こちらは堅牢かつ本番環境に対応した包括的なソリューションでして、
> ぜひ詳しく掘り下げさせていただければと存じます。

日本語だと敬語の重ね掛けも加わって、実際に知りたい一行に辿り着くまでが遠い。
英語でも "Great question!" "You're absolutely right!" "delve into" が延々と続く。

内容を変えずに、この「アシスタント語」だけを剥がしたい。それが declaude です。

## 仕組み

3行でいうと:

1. Claude Code の **MessageDisplay フック**が、Claude の返答が確定した *後* に発火する
2. 本文をこちらの GPU（vLLM + Qwen2.5-14B-AWQ）に投げて、平易な文章に書き換える
3. 書き換え後のテキストを**画面にだけ**表示する

ここが重要で、**書き換えは Claude のトークンを 1 つも消費しません**。
Anthropic の API を経由しないからです。会話履歴も汚れないので、次のターンの
コンテキストは元のまま。表示レイヤーだけが変わります。

```
Claude が生成 → フックが横取り → 自前 GPU で書き換え → 画面に表示
                                    ↑ ここは Claude 非経由
```

## 使い方

MCP クライアントとして繋ぐ場合はコマンド 1 行で済みます。API キーの貼り付けは不要で、
ブラウザが開いてサインインするだけです（OAuth 2.1 + PKCE）。

```bash
claude mcp add --transport http declaude https://speak-english.tenken.co/mcp
```

Markdown ファイルをまるごと投げることもできます。散文だけが書き換わり、
コードブロック・見出し・表はバイト単位でそのまま残ります。

```bash
curl -X POST https://speak-english.tenken.co/v1/documents \
  -H "Authorization: Bearer $DECLAUDE_TOKEN" \
  -F "file=@notes.md" -o notes.declauded.md
```

## 日本語での挙動

開発中に踏んだ一番厄介なバグがこれでした。日本語を入れると **中国語で返ってくる**。
小さいオープンモデルにありがちな挙動です。

対策は 2 段構えにしました。

1. システムプロンプトで「入力と同じ言語で出力せよ。人間の言語間で翻訳するな」と固定
2. それでも破れるので、**出力側で検査**する。入力と出力の Unicode スクリプトを比較して、
   違っていたら書き換えを捨てて原文を返す

プロンプトは「お願い」であって「保証」ではないので、境界で検証する。
仮名が 1 文字でもあれば日本語と判定するため、日本語 → 中国語のすり替えも検出できます。

## 技術構成

| 層 | 構成 |
|---|---|
| モデル | vLLM + Qwen2.5-14B-Instruct-AWQ（L4 スポットインスタンス、us-east1） |
| ゲートウェイ | FastAPI / Cloud Run（us-central1）、内部 LB 経由でモデルへ |
| 認証 | Clerk（GitHub / Google / メールコード）+ 失効しない API キー |
| 課金 | Stripe（無料枠: 100 翻訳/月・5 ドキュメント/月） |

プロンプトのログは vLLM 側で明示的に無効化しています（`--disable-log-requests`）。
本文はメモリ上で処理して破棄、ディスクにも DB にもログにも残しません。

## 元ネタ

[gvzdv/claudish-to-english](https://github.com/gvzdv/claudish-to-english) という
ローカル Ollama 用フックが元になっています。あれを Ollama なしで、
チーム共有・複数クライアント対応にしたのが declaude です。

- サイト: https://speak-english.tenken.co
- ソース: https://github.com/tenkenco/declaude （MIT）
