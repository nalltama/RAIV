# Realtime AI Image Viewer (RAIV)

RAIV は、Real-CUGAN / Real-ESRGAN、または別途導入したTopaz Gigapixel AIによる画像の超解像・復元処理を自動で行いながら閲覧できる Windows 向け画像ビューアーです。画像を開くだけで処理済み画像を表示し、処理前後の比較、ページ送り、ズーム、パン、サムネイル移動などを行えます。高速なページ送りと先読みを重視しており、大量の画像を快適に閲覧することを目指しています。`RAIV` の開発は Codex を用いた完全AIコーディングで行われています。

English version is below the Japanese section.

## ダウンロード

最新版は GitHub Releases ページからダウンロードできます。

- [RAIV Releases](https://github.com/nalltama/RAIV/releases)

配布ZIPは2種類あります。

- `RAIV-vX.Y.Z-pyw.zip`: 無駄のないpyw版。容量が小さく、Pythonをインストール済みの環境向けです。
- `RAIV-vX.Y.Z-standalone.zip`: スタンドアロン版。容量は大きくなりますが、PythonをPCへインストールしなくても `RAIV.exe` から起動できます。

通常は、Pythonを入れたくない場合はスタンドアロン版、容量を抑えたい場合やPython環境が既にある場合はpyw版を選んでください。ダウンロードしたZIPを任意のフォルダへ展開して使います。

## 初回セットアップ

スタンドアロン版では、このセットアップは不要です。

pyw版を使う場合は、Python をインストールしたあと、最初に次を実行してください。Python をまだ入れていない場合は、公式サイトからWindows版をインストールできます。

- [Python Downloads](https://www.python.org/downloads/)

```powershell
install_support.bat
```

この bat は以下の Python パッケージを導入します。

- `PySide6`: アプリ画面
- `Pillow`: 高品質な表示サイズ変換
- `opencv-python-headless`: Lanczos4 用の任意パッケージ
- `py7zr`: 7z/CB7 アーカイブ対応
- `rarfile`: RAR/CBR アーカイブ対応の補助
- `novelai-sdk`: NovelAI 画像生成API連携

RAR/CBR は環境によって、別途 7-Zip、UnRAR、bsdtar のいずれかが必要です。

## アップデート

新しいバージョンへ更新する場合は、GitHub Releases ページから使用中の配布形式に合わせて新しい `RAIV-vX.Y.Z-pyw.zip` または `RAIV-vX.Y.Z-standalone.zip` をダウンロードし、展開した中身で既存のRAIVフォルダを上書きしてください。

通常、`setting.json` や `folder_history.json` は配布ZIPに含まれていないため、既存フォルダを上書きしても設定やフォルダ履歴は残ります。不安な場合は、上書き前にRAIVフォルダ全体を別の場所へコピーしてバックアップしてください。

## 起動

スタンドアロン版では `RAIV.exe` を実行します。

pyw版では通常 `run_raiv.pyw` を実行します。Python の関連付け環境によって `.pyw` のダブルクリック起動ができない場合は、`install_pyw_association.bat` を実行すると、現在のユーザーの `.pyw` 関連付けを `where pyw` で見つかる `pyw.exe` に設定できます。

Windows のバージョンや既定アプリ設定によっては、バッチ実行後に `run_raiv.pyw` をダブルクリックした時、`アプリを選択して .pyw ファイルを開く` 画面が表示されることがあります。その場合は `pyw.exe` を選び、`常に使う` を押してください。以後は `run_raiv.pyw` をダブルクリックするだけで起動できます。

関連付けを変更せずに起動したい場合は `run_raiv.bat`、または次のコマンドで起動できます。`run_raiv.vbs` からでも起動できますが、VBScript はWindowsで将来的に廃止予定のため、環境によっては将来起動できなくなる可能性があります。通常は `run_raiv.pyw` または `run_raiv.bat` を使用してください。

```powershell
python .\raiv.py
```

ログは右ペインの全般タブにある `ログを表示` でオン/オフできます。

## 画像を開く

- 画像ファイル、フォルダ、ZIP/CBZ、RAR/CBR、7z/CB7 をドラッグアンドドロップ
- `O` キーで画像ファイルを選択
- `F` キーでフォルダを選択

画像ファイルを開いた場合は、まずその画像を表示し、同じフォルダ内の画像一覧はあとから取得します。

アニメーションGIFとアニメーションPNG（APNG）は表示中に再生できます。サムネイルは先頭フレームを表示し、アニメーション画像は拡大エンジンとAI彩色の処理対象外です。

JPEG XR / HD Photo 系の `.jxr`、`.wdp`、`.hdp` も表示できます。これらのHDR画像は、アプリやモニタへHDR信号として出力するのではなく、白飛びや黒つぶれを抑えるためにSDR表示用の色域・階調へトーンマッピングして互換表示します。HDR画像は表示互換を目的とするため、拡大エンジンの処理対象外です。
HDR画像を表示している時は、画像調整タブの `HDR互換表示の明るさ` でSDR互換表示へ変換する時の明るさを調整できます。100%が自動トーンマップの基準値で、`100%に戻す` でリセットできます。

## 画像処理エンジン

右ペインのエンジン設定タブで、Real-CUGAN、Real-ESRGAN、Gigapixel AIを切り替えられます。

Real-CUGAN:

```text
tools\realcugan-ncnn-vulkan\realcugan-ncnn-vulkan.exe
```

Real-ESRGAN:

```text
tools\realesrgan-ncnn-vulkan\realesrgan-ncnn-vulkan.exe
```

Gigapixel AIはRAIVへ同梱されません。利用にはTopaz Gigapixel AIのインストールと、コマンドライン機能を利用できるProライセンスが必要です。既定の場所で検出できない場合は、`エンジンexeを選択`から`gigapixel.exe`を指定してください。

開発者はGigapixel AIを保有していないため、この連携機能は公式ドキュメントで確認できる仕様に基づいて実装しており、実機での動作は未確認です。

Real-CUGAN はアニメ/イラスト画像向けに学習・調整された超解像モデルです。写真や一般画像では Real-ESRGAN が適する場合がありますが、アニメ、イラスト、漫画調の画像では、線や塗りの質感を保ちやすい Real-CUGAN の方が自然で高品質な結果になる可能性があります。まず Real-CUGAN を試し、必要に応じて Real-ESRGAN のアニメ向けモデルと比較してください。

Real-ESRGAN モデル:

- `realesr-animevideov3`: アニメ/イラスト向けの軽量モデル
- `realesrgan-x4plus`: 写真や一般画像向け
- `realesrgan-x4plus-anime`: アニメ/イラスト向けの x4plus 系モデル

`realesr-animevideov3`では2倍/3倍/4倍、x4plus系モデルでは4倍を選択できます。Gigapixel AIではStandard、High Fidelity、Low Resolution、Text & Shapes、Art & CGのCore Modelsと2倍/3倍/4倍/6倍を選択できます。

## 主な設定

エンジン設定:

- エンジンに応じたモデル、倍率、ノイズ、tile（0は自動。内蔵GPUなどでメモリ不足になる場合は小さめの値を指定可能）
- Gigapixel AIのDenoise、Sharpen、Fix Compression、Face Recovery
- エンジン先読み枚数
- 指定縦解像度以上の画像を拡大処理しない設定
- 縦サイズ閾値へ届く最小倍率を画像ごとに自動選択
- 拡大結果を倍率フォルダへ保存
- 倍率フォルダがあれば表示に使う（現在のエンジン、モデル、倍率に完全一致するフォルダのみ使用）

全般:

- ビューアー先読み枚数
- 背景色
- 見開き表示による漫画の左右2枚表示
- 横長画像を既に見開きのページとして扱う1枚表示
- 比較モード、比較スライダー、境界線色、境界線太さ
- 表示リセット、ページ送り間隔
- 現在ページ位置の表示とスライダー移動
- ページ位置スライダーとサムネイル列の左右入れ替え（右綴じ）
- 画面下部サムネイルの表示と固定/自動表示
- 最後/最初でページ送りした時のループ
- ページ送り時にズーム、表示位置、回転/反転状態を維持
- 回転時にズーム倍率を維持するか、回転後の画像全体が収まるようにフィットし直すかの切り替え
- マウス横スクロールのページ送り有効化と方向反転
- 全画面時のマウスカーソル非表示
- ログ表示
- 内部プロファイリング表示

画像調整:

- 表示上だけの明るさ、コントラスト、ガンマ、シャープネス調整
- 画像の回転、左右反転、上下反転、表示リセットをボタンから実行
- GIMP `.cur` トーンカーブファイルを使った表示補正
- モノクロ漫画を疑似4色刷り風に表示
- トーンカーブを画面上で確認しながら調整し、`.cur` として保存

`.cur` ファイルはアプリフォルダ内の `cur` フォルダから読み込みます。

AI彩色:

- ComfyUI API連携
- ComfyUI初期設定と推奨checkpoint / ControlNetのダウンロード
- SDXL向けLineart ControlNetを使った構造保持
- API形式のworkflow JSONを使った現在画像の彩色
- LoadImage / SaveImage ノードの検出
- 彩色結果を `RAIV_colorized` フォルダへ保存するか、一時ファイルとして表示
- `RAIV_colorized` に彩色済み画像があれば表示に使用
- 彩色結果を表示に使うかどうかのオン/オフ
- AI彩色の先行処理オン/オフと先読み枚数設定
- 彩色強度、線画保持、彩度補正、輝度保持、Positive/Negative promptの調整
- 手動彩色時は既存の彩色結果を上書きし、先行処理時は彩色済みページをスキップ

NovelAI生成:

- 永続APIトークンを使ったNovelAIのテキストから画像生成
- 保存先フォルダ指定（既定は `RAIV_generated`）と保存名テンプレート。`{YYYY}`、`{MM}`、`{DD}`、`{HH}`、`{mm}`、`{ss}`、`{date}`、`{time}`、`{seed}` を年、月、日、時、分、秒、日付まとめ（YYYYMMDD）、時刻まとめ（HHmmss）、シード値へ置換できます。`/` または `\` でサブフォルダを入れ子にでき、シード値、日付/シード値、日付/時刻、日付/時刻_シード値、カスタムのプリセットを選択できます（既定はシード値）
- プロンプト、除外したい要素、モデル、サンプラー、ノイズスケジュール、シード値、画像解像度、ステップ数、プロンプトガイダンス、プロンプトガイダンスの再調整、多様性、生成枚数の指定。解像度から1回に生成可能な枚数を計算し、上限を超える枚数は選択不可。解像度変更で上限が下がった場合だけ選択枚数を上限へ合わせ、解像度自体が上限外の場合は入力欄の隣へ表示
- プロンプト欄と除外したい要素欄は個別に折り畳み可能。開閉状態は設定へ保存
- プロンプト分解モードで再構築したプロンプトと除外したい要素を各一覧の下に表示可能
- 保存先、保存名、APIトークン、品質タグ、モデル、サンプラーなどを折りたたみ可能な詳細設定へ整理し、詳細設定の開閉状態を保存
- アニメモード / ケモノモード切替（ケモノモードでは生成時に `fur dataset` をプロンプト先頭へ追加）
- プロンプトをタグ単位へ分解し、追加、有効/無効、直接編集、強調/抑制、上下ボタン/ドラッグ並び替え、削除を行う編集モード。名前付きフォルダを入れ子にしてタグを整理し、折りたたみやドラッグによるフォルダ間移動もできます。フォルダの「ランダム」をオンにすると、有効な内容を `|` でつないで全体を `||` で囲み、ランダム選択構文として送信します。タグとフォルダの追加先は選択行に影響されず、既定では一覧の末尾、「先頭に追加する」をオンにすると先頭になります。入力欄に文字がある状態でフォルダ追加を押すと、その文字をフォルダ名に使います（入力欄からのタグ追加は1行扱い。既存テキストの分解時は括弧、`||...|...||` のランダム選択構文、`1.2::tagA, tagB::` や `-1::tag::` などの数値重み指定構文の外側にある`, `を区切りとして扱います。単独の `::` は未閉じの強調/抑制括弧を閉じるものとして扱います）
- プロンプト分解モードで無効化したタグは、通常モードではRAIV専用マーカー `<<RAIV_DISABLED_PROMPT>>...<</RAIV_DISABLED_PROMPT>>` で保持されます。このマーカー内の内容はNovelAI送信時には除外されます。
- 分解モードのフォルダ構造は、通常モードではRAIV専用マーカー `<<RAIV_PROMPT_FOLDER:...>>...<</RAIV_PROMPT_FOLDER>>` で保持されます。ランダム設定も専用の `<<RAIV_PROMPT_RANDOM_FOLDER:...>>` マーカーで保持します。フォルダ名はマーカー内へ安全に符号化され、NovelAI送信時にはフォルダマーカーを除外してランダム選択構文へ変換します。ユーザーが直接入力した `||...|...||` を自動でフォルダ化することはありません。
- 「フォルダ削除時、中身ごと消す」は既定でオフです。オフではフォルダだけを削除して中のタグやフォルダを同じ位置へ残し、オンでは中身もまとめて削除します。
- タグプリセットの保存、読込、削除（`setting.json` とは別の `novelai_prompt_presets.json` に保存）
- 品質タグ追加と除外プリセット（強い、弱い、ケモノモード、人間に重点を置く、指定なし）の指定
- Enterで生成、Shift+Enterで改行する入力オプション
- NovelAI標準に近いサイズプリセットと自由な幅 / 高さ入力
- `novelai-sdk` による推定消費Anlas表示（実際の消費量と完全一致する保証はありません）
- 生成後の自動表示と選択中の拡大エンジンへの処理キュー投入
- 生成設定を画像ごとのJSONサイドカーに保存
- NovelAI生成画像のPNGメタデータをインポートし、プロンプト、除外したい要素、品質タグ、除外プリセット、モデル、サンプラー、ノイズスケジュール、画像サイズ、ステップ数、プロンプトガイダンス、シード値などを生成設定へ反映

永続APIトークンは `setting.json` ではなく、Windows DPAPIで暗号化した `novelai_token.dat` に保存されます。タグプリセットは `novelai_prompt_presets.json` に保存されます。共有PCや配布用ZIPを作る場合は、これらの個人設定ファイルを同梱しないでください。

NovelAI生成機能を利用するには、ユーザー自身のNovelAI Persistent API Tokenが必要です。RAIVはNovelAI公式アプリではなく、Anlatan / NovelAIとは提携していません。NovelAIの利用はNovelAIの利用規約に従ってください。RAIVは開発者や配布者のAPIトークンを同梱せず、NovelAIの制限、Anlas消費、認証を回避する目的の機能も提供しません。

その他:

- Language（日本語 / English）
- テーマ（Windowsの設定に同期 / ライトテーマ / ダークテーマ）。QtのWindows連携を使い、RAIV独自の配色は使用しません
- AI彩色、NovelAI生成、キーコンフィグのタブ表示/非表示
- 右ペインの左右移動。境界の三本線グリップをドラッグして幅を変更可能
- 拡大縮小時の高品質補完
- 表示リサンプル方式: Lanczos3、Lanczos4、Bicubic、Area
- アプリの二重起動禁止
- 最後に開いていた画像を次回起動時に開く
- フォルダごとに最後に開いていた画像を記録
- バージョン表示と手動アップデート確認
- 次回起動時の古い一時ファイル削除

サムネイル列は下端に表示されます。固定表示では画像表示領域を少し使い、自動表示ではビューアー下端へマウスを近づけた時だけ重ねて表示します。サムネイルの大きさは列の高さ変更に合わせて自動調整されます。

キーコンフィグ:

- 各機能につき、キーボード1つ、マウスボタン1つを割り当て可能
- 設定値をクリックしてからキーまたはマウスボタンを押すと割当を変更
- `Ctrl`、`Shift`、`Alt` との組み合わせ指定に対応
- 設定中に `Esc` を押すと未割当に戻る
- `Space` の次ページ送り、`Backspace` の前ページ送りは固定

拡大縮小時の高品質補完をオンにすると、原寸と異なる表示サイズの画像を高品質に作成して保持します。ズーム操作中は速度を優先し、操作が止まってから高品質表示へ切り替わります。オフにすると標準の高速表示になります。

## 操作

マウス:

- ホイール: 前後ページ送り
- 横スクロール: 設定で有効にした場合のみ前後ページ送り
- `Ctrl` + ホイール: ズーム
- `Ctrl` + 左ドラッグ上下: 上でズームイン、下でズームアウト
- 左ドラッグ: パン
- 比較モード中のドラッグ: 比較境界線の移動
- 比較モード中の `Shift` + ドラッグ: 設定に応じてパン/境界線移動を切り替え
- ホイールクリック: ボーダーレス全画面の切り替え（キーコンフィグで変更可能）
- 左ダブルクリック: 表示を中央へリセット（キーコンフィグで変更可能）
- 右ダブルクリック: 等倍表示（キーコンフィグで変更可能）
- 戻る/進むボタン: フォルダ内の先頭/末尾へ移動（キーコンフィグで変更可能）

キーボード:

- `O`: 画像を開く（キーコンフィグで変更可能）
- `F`: フォルダを開く（キーコンフィグで変更可能）
- 上カーソル: 親フォルダへ移動（キーコンフィグで変更可能）
- 下カーソル: 次フォルダへ移動（キーコンフィグで変更可能）
- `Ctrl` + 下カーソル: 子フォルダへ移動（キーコンフィグで変更可能）
- 左カーソル: 次ページへ移動（キーコンフィグで変更可能）
- 右カーソル: 前ページへ移動（キーコンフィグで変更可能）
- `F3`: サムネイル列の固定/自動表示を切り替え（キーコンフィグで変更可能）
- `F4`: 右ペインの固定/自動表示を切り替え（キーコンフィグで変更可能）
- `W`: 見開き表示を切り替え（キーコンフィグで変更可能）
- `Q`: 見開き表示中に1ページ送り（キーコンフィグで変更可能）
- `E`: 見開き表示中に1ページ戻し（キーコンフィグで変更可能）
- `T`: トーンカーブ補正を切り替え（キーコンフィグで変更可能）
- `R`: 画像を右に1度回転（キーコンフィグで変更可能）
- `L`: 画像を左に1度回転（キーコンフィグで変更可能）
- `Shift` + `R`: 画像を右に90度回転（キーコンフィグで変更可能）
- `Shift` + `L`: 画像を左に90度回転（キーコンフィグで変更可能）
- `H`: 画像を左右反転（キーコンフィグで変更可能）
- `V`: 画像を上下反転（キーコンフィグで変更可能）
- `G`: NovelAI画像生成（キーコンフィグで変更可能）
- `Delete`: 現在画像を削除（キーコンフィグで変更可能）
- `Space`: 次ページへ移動
- `Backspace`: 前ページへ移動

フォルダ移動では、RAIVが作成した倍率フォルダは移動先候補から除外されます。

## 保存フォルダ

拡大結果の保存を有効にすると、元画像と同じフォルダ配下にエンジン/倍率に応じたサブフォルダを作成します。

例:

- `realcugan_x2`
- `realesrgan_realesrgan-x4plus_x4`

アーカイブ表示中は保存先フォルダがないため、倍率フォルダ保存と倍率フォルダ読み込みは無効になります。

## 設定と一時ファイル

設定はアプリと同じフォルダの `setting.json` に保存されます。設定ファイルがない場合は初期設定で起動します。フォルダごとの最後に開いていた画像の履歴は、設定ファイルが大きくなりすぎないよう `folder_history.json` に分けて保存されます。保存件数はその他タブで変更でき、`0` にすると無制限です。

一時ファイルは OS の一時フォルダに RAIV 用の接頭辞付きで作成され、通常終了時に削除されます。クラッシュなどで残った場合に備えて、その他タブから次回起動時の古い一時ファイル削除を予約できます。

## アーカイブ対応

ZIP/CBZ は標準ライブラリで展開します。7z/CB7 は `py7zr` または外部 7-Zip を使います。RAR/CBR は `rarfile`、または外部の 7z/7za/7zr、UnRAR、bsdtar を使います。

## ライセンスと同梱物

RAIV 本体は MIT License です。詳細は `LICENSE` を参照してください。

同梱している外部ツール:

- Real-CUGAN ncnn Vulkan: MIT License  
  付属ファイル: `tools\realcugan-ncnn-vulkan\LICENSE`, `tools\realcugan-ncnn-vulkan\README.md`
- Real-ESRGAN ncnn Vulkan / Real-ESRGAN: BSD 3-Clause License  
  付属ファイル: `tools\realesrgan-ncnn-vulkan\LICENSE`, `tools\realesrgan-ncnn-vulkan\README_windows.md`

Topaz Gigapixel AIは同梱物ではありません。利用者が別途導入した製品を、その製品ライセンスに従って外部CLIとして呼び出します。

配布時は `tools` 配下の exe、DLL、モデル、README、LICENSE を欠落させないようにしてください。

---

# Realtime AI Image Viewer (RAIV)

RAIV is a Windows image viewer that automatically displays images processed with Real-CUGAN, Real-ESRGAN, or a separately installed copy of Topaz Gigapixel AI. Open an image and RAIV can show the processed result, compare before/after images, browse pages, zoom, pan, and navigate with thumbnails. RAIV focuses on fast page navigation and prefetching so large image folders can be browsed comfortably. Development of `RAIV` is done through fully AI-assisted coding with Codex.

## Download

Download the latest version from the GitHub Releases page.

- [RAIV Releases](https://github.com/nalltama/RAIV/releases)

There are two release ZIPs.

- `RAIV-vX.Y.Z-pyw.zip`: lightweight pyw edition. It is smaller and intended for environments where Python is already installed.
- `RAIV-vX.Y.Z-standalone.zip`: standalone edition. It is larger, but it does not require installing Python on the PC and can be launched with `RAIV.exe`.

Choose the standalone edition if you do not want to install Python. Choose the pyw edition if you already have Python or want a smaller download. Extract the downloaded ZIP to any folder.

## First Setup

The standalone edition does not require this setup.

For the pyw edition, after installing Python, run the following command first. If Python is not installed yet, install the Windows version from the official site.

- [Python Downloads](https://www.python.org/downloads/)

```powershell
install_support.bat
```

This batch file installs the following Python packages:

- `PySide6`: application UI
- `Pillow`: high-quality display resizing
- `opencv-python-headless`: optional package for Lanczos4
- `py7zr`: 7z/CB7 archive support
- `rarfile`: helper package for RAR/CBR archive support
- `novelai-sdk`: NovelAI image generation API integration

Depending on your environment, RAR/CBR support may also require 7-Zip, UnRAR, or bsdtar.

## Updating

To update to a new version, download the new `RAIV-vX.Y.Z-pyw.zip` or `RAIV-vX.Y.Z-standalone.zip` from the GitHub Releases page according to the edition you use, then overwrite the existing RAIV folder with the extracted files.

Normally, `setting.json` and `folder_history.json` are not included in the release ZIP, so overwriting the folder keeps your settings and folder history. If you want to be extra careful, copy the whole RAIV folder somewhere else as a backup before overwriting it.

## Launch

For the standalone edition, run `RAIV.exe`.

For the pyw edition, usually run `run_raiv.pyw`. If double-clicking `.pyw` files does not work because of Python file association settings, run `install_pyw_association.bat` to associate `.pyw` with the `pyw.exe` found by `where pyw` for the current Windows user.

Depending on your Windows version and default app settings, double-clicking `run_raiv.pyw` after running the batch file may still show an `Open .pyw file with` app selection dialog. In that case, choose `pyw.exe` and click `Always`. After that, `run_raiv.pyw` should launch by double-clicking.

If you do not want to change file associations, run `run_raiv.bat`, or launch it manually. `run_raiv.vbs` can also launch RAIV, but VBScript is planned for deprecation in Windows, so it may stop working in some future environments. Prefer `run_raiv.pyw` or `run_raiv.bat` for normal use.

```powershell
python .\raiv.py
```

Logs can be shown or hidden from `Show log` in the General tab.

## Opening Images

- Drag and drop an image file, folder, ZIP/CBZ, RAR/CBR, or 7z/CB7 archive
- Press `O` to select an image file
- Press `F` to select a folder

When an image file is opened, RAIV displays it first and then collects the rest of the images in the same folder.

Animated GIF and animated PNG (APNG) files play while displayed. Thumbnails use the first frame, and animated images are excluded from upscaling and AI colorization processing.

RAIV can also display JPEG XR / HD Photo files: `.jxr`, `.wdp`, and `.hdp`. HDR images are not output as an HDR signal by the application; they are tone-mapped into an SDR-compatible color and tonal range to avoid harsh clipping and crushed shadows. HDR image support is intended for compatible viewing, so these files are excluded from processing by the upscaling engines.
While an HDR image is displayed, the Image Adjustment tab enables `HDR compatible brightness` so you can adjust the brightness used during SDR-compatible conversion. 100% is the baseline for the automatic tone map, and `Reset to 100%` restores it.

## Processing Engines

Use the Engine Settings tab in the right panel to switch between Real-CUGAN, Real-ESRGAN, and Gigapixel AI.

Real-CUGAN:

```text
tools\realcugan-ncnn-vulkan\realcugan-ncnn-vulkan.exe
```

Real-ESRGAN:

```text
tools\realesrgan-ncnn-vulkan\realesrgan-ncnn-vulkan.exe
```

Gigapixel AI is not bundled with RAIV. It requires an installed copy of Topaz Gigapixel AI and a Pro license that enables command-line use. If RAIV cannot detect it in the default location, select `gigapixel.exe` with `Select engine exe`.

The developer does not own Gigapixel AI. This integration is implemented from specifications available in the official documentation and has not been verified with an installed copy of the product.

Real-CUGAN is trained and tuned for anime/illustration images. Real-ESRGAN may be better for photos and general images, but for anime, illustration, and manga-like artwork, Real-CUGAN is more likely to preserve linework and flat-color texture naturally. Try Real-CUGAN first for those images, then compare it with Real-ESRGAN's anime-oriented models if needed.

Real-ESRGAN models:

- `realesr-animevideov3`: lightweight model for anime/illustration images
- `realesrgan-x4plus`: model for photos and general images
- `realesrgan-x4plus-anime`: x4plus-style model for anime/illustration images

`realesr-animevideov3` supports 2x/3x/4x, while the x4plus models support 4x. Gigapixel AI provides the Standard, High Fidelity, Low Resolution, Text & Shapes, and Art & CG Core Models with 2x/3x/4x/6x choices.

## Main Settings

Engine settings:

- Engine-specific model, scale, denoise, and tile options (0 is automatic; smaller tile values can be set for low-memory GPUs)
- Gigapixel AI Denoise, Sharpen, Fix Compression, and Face Recovery
- Engine prefetch count
- Skip processing for images above a specified vertical resolution
- Automatically choose the smallest per-image scale that reaches the vertical threshold
- Save processed images to a scale folder
- Use an existing scale folder as display cache (only when it exactly matches the current engine, model, and scale)

General:

- Viewer prefetch count
- Background color
- Spread view for manga pages
- Show landscape images as a single page when they are already spread pages
- Compare mode, compare slider, divider color, divider width
- Reset view, page navigation interval
- Current page slider and page count
- Reverse page slider direction and thumbnail strip direction for right-to-left reading
- Bottom thumbnail strip with pinned/auto display modes
- Wrap around at first/last page
- Preserve zoom, pan, rotation, and flip state during page navigation
- Choose whether rotation preserves zoom or refits the whole rotated image
- Horizontal mouse wheel page navigation and direction reverse
- Hide mouse cursor in fullscreen
- Log display
- Internal profiling display

Image Adjustment:

- Display-only brightness, contrast, gamma, and sharpness adjustment
- Buttons for image rotation, horizontal/vertical flip, and display reset
- Display adjustment using GIMP `.cur` tone curve files
- Pseudo four-color printing style for monochrome manga
- Edit tone curves while viewing the graph and save them as `.cur`

`.cur` files are loaded from the `cur` folder inside the application folder.

AI Colorize:

- ComfyUI API integration
- ComfyUI initial setup and recommended checkpoint / ControlNet download
- Structure preservation using an SDXL Lineart ControlNet
- Colorize the current image using an API-format workflow JSON
- Detect LoadImage / SaveImage nodes
- Save colorized results to the `RAIV_colorized` folder or display them as temporary files
- Use existing colorized images in `RAIV_colorized` for display
- Toggle whether colorized results are used for display
- Toggle AI colorization prefetch and set its prefetch count
- Adjust color strength, line preservation, saturation correction, luminance preservation, and positive/negative prompts
- Manual colorization overwrites existing results; prefetch skips already colorized pages

NovelAI Generation:

- NovelAI text2img generation using a Persistent API Token
- Configurable output folder (default: `RAIV_generated`) and output-name template. `{YYYY}`, `{MM}`, `{DD}`, `{HH}`, `{mm}`, `{ss}`, `{date}`, `{time}`, and `{seed}` expand to the date/time components, full date (YYYYMMDD), full time (HHmmss), and generation seed. Use `/` or `\` to create nested subfolders, with Seed, Date/Seed, Date/Time, Date/Time_Seed, and Custom presets (default: Seed)
- Prompt / Undesired Content, Model, Sampler, Noise Schedule, Seed, Image Resolution, Steps, Prompt Guidance, Prompt Guidance Rescale, Variety Boost, and Number of Images settings. The per-request image limit is calculated from the resolution, unsupported counts are disabled, and the selected count is reduced only when a resolution change lowers the limit. Resolutions beyond the supported limit are indicated beside the size fields.
- Prompt and Undesired Content sections can be collapsed independently, with their expanded states saved in settings
- Optionally show the reconstructed Prompt and Undesired Content below each list in prompt decomposition mode
- Output folder, output name, API token, quality tags, model, and sampler settings are grouped under collapsible advanced settings, with the expanded/collapsed state saved
- Anime / Furry mode switch. Furry mode adds `fur dataset` to the beginning of the generation prompt.
- Optional tag-list prompt editor with add, enable/disable, direct edit, emphasize/suppress, up/down and drag reorder controls, and delete. Tags can be organized in nested named folders, collapsed, and dragged between folders. Enabling Random on a folder joins its active contents with `|` and wraps the result in `||` when sending the prompt. New tags and folders ignore the selected row and are added to the bottom by default, or to the top when Add at top is enabled. When the input field contains text, Add folder uses it as the folder name. Text added as a tag is kept as one row; decomposing existing text splits on `, ` outside brackets, `||...|...||` random-choice syntax, and numeric weight syntax such as `1.2::tagA, tagB::` or `-1::tag::`. A standalone `::` is treated as closing unbalanced emphasis/suppression brackets.
- Tags disabled in prompt decomposition mode are preserved in normal mode with RAIV-specific markers: `<<RAIV_DISABLED_PROMPT>>...<</RAIV_DISABLED_PROMPT>>`. Content inside those markers is excluded when sending prompts to NovelAI.
- Folder structure from prompt decomposition mode is preserved in normal mode with RAIV-specific markers: `<<RAIV_PROMPT_FOLDER:...>>...<</RAIV_PROMPT_FOLDER>>`. Random folder settings are preserved with a separate `<<RAIV_PROMPT_RANDOM_FOLDER:...>>` marker. Folder names are safely encoded in the marker; when sending prompts to NovelAI, the markers are removed and random folders are converted to random-choice syntax. User-written `||...|...||` syntax is never converted into a folder automatically.
- `Delete folder contents with folder` is off by default. When off, deleting a folder keeps its tags and nested folders at the same position; when on, its contents are deleted with it.
- Save, load, and delete tag presets. Presets are stored in `novelai_prompt_presets.json`, separate from `setting.json`.
- Add Quality Tags and Undesired Content preset selection (Strong, Light, Furry Focus, Human Focus, None)
- Enter-to-generate option, with Shift+Enter inserting a line break
- NovelAI-like size presets plus custom width / height input
- Estimated Anlas cost using `novelai-sdk` (not guaranteed to exactly match the actual charge)
- Automatically display generated images and enqueue them for the selected upscaling engine
- Save generation settings as a JSON sidecar for each generated image
- Import PNG metadata from NovelAI-generated images and apply prompt, undesired content, quality tags, undesired content preset, model, sampler, noise schedule, size, steps, prompt guidance, seed, and related settings

The Persistent API Token is stored in `novelai_token.dat` encrypted with Windows DPAPI, not in `setting.json`. Tag presets are stored in `novelai_prompt_presets.json`. On shared PCs or when creating release ZIPs, do not include these personal files.

NovelAI Generation requires the user's own NovelAI Persistent API Token. RAIV is not an official NovelAI app and is not affiliated with Anlatan / NovelAI. Use of NovelAI is subject to NovelAI's terms of service. RAIV does not bundle a developer or distributor API token and does not provide features intended to bypass NovelAI limits, Anlas usage, or authentication.

Other:

- Language (Japanese / English)
- Theme (Follow Windows settings / Light theme / Dark theme). This uses Qt's Windows integration rather than a RAIV-specific color palette.
- Show/hide AI Colorize, NovelAI Generation, and Key Config tabs
- Move the side panel between the left and right side, and drag the three-line boundary grip to resize it
- High-quality scaling for zoomed/resized display
- Display resampling method: Lanczos3, Lanczos4, Bicubic, Area
- Prevent multiple app instances
- Open the last viewed image on startup
- Remember the last viewed image for each folder
- Version display and manual update check
- Cleanup old temporary files on next startup

The thumbnail strip appears at the bottom. In pinned mode it uses part of the image area; in auto mode it overlays the viewer only when the mouse approaches the bottom edge. Thumbnail size is adjusted automatically from the strip height.

Key configuration:

- One keyboard binding and one mouse binding can be assigned to each action
- Click a binding value, then press a key or mouse button to change it
- `Ctrl`, `Shift`, and `Alt` modifiers are supported
- Press `Esc` while assigning to clear a binding
- `Space` for next page and `Backspace` for previous page are fixed

When high-quality scaling is enabled, RAIV creates and keeps high-quality display-size images. During zoom interaction it prioritizes speed, then switches to high-quality rendering after the operation stops. When disabled, RAIV uses the standard fast display path.

## Controls

Mouse:

- Wheel: previous/next page
- Horizontal wheel: previous/next page only when enabled
- `Ctrl` + wheel: zoom
- `Ctrl` + left-drag up/down: zoom in/out
- Left-drag: pan
- Drag in compare mode: move compare divider
- `Shift` + drag in compare mode: switch pan/divider behavior depending on the setting
- Middle click: toggle borderless fullscreen, configurable
- Left double click: reset view to center, configurable
- Right double click: actual-size view, configurable
- Back/Forward mouse buttons: jump to first/last image in the folder, configurable

Keyboard:

- `O`: open image, configurable
- `F`: open folder, configurable
- Up arrow: move to parent folder, configurable
- Down arrow: move to next folder, configurable
- `Ctrl` + Down arrow: move to child folder, configurable
- Left arrow: next page, configurable
- Right arrow: previous page, configurable
- `F3`: toggle thumbnail strip pinned/auto mode, configurable
- `F4`: toggle right panel pinned/auto mode, configurable
- `W`: toggle spread view, configurable
- `Q`: shift one page forward in spread view, configurable
- `E`: shift one page backward in spread view, configurable
- `T`: toggle tone curve adjustment, configurable
- `R`: rotate image right by 1 degree, configurable
- `L`: rotate image left by 1 degree, configurable
- `Shift` + `R`: rotate image right by 90 degrees, configurable
- `Shift` + `L`: rotate image left by 90 degrees, configurable
- `H`: flip image horizontally, configurable
- `V`: flip image vertically, configurable
- `G`: generate a NovelAI image, configurable
- `Delete`: delete current image, configurable
- `Space`: next page
- `Backspace`: previous page

Folder navigation ignores scale folders created by RAIV.

## Save Folders

When saving processed results is enabled, RAIV creates an engine/scale-specific subfolder next to the original image.

Examples:

- `realcugan_x2`
- `realesrgan_realesrgan-x4plus_x4`

While viewing archives, scale-folder saving and scale-folder cache loading are disabled because there is no normal output folder.

## Settings and Temporary Files

Settings are saved as `setting.json` in the application folder. If the file does not exist, RAIV starts with default settings. Per-folder last-viewed image history is saved separately as `folder_history.json` so the main settings file does not grow too large. The maximum number of history entries can be changed in the Other tab; set it to `0` for unlimited history.

Temporary files are created under the OS temporary folder with RAIV-specific prefixes and are removed on normal exit. If files remain after a crash, you can reserve cleanup of old temporary files from the Other tab for the next startup.

## Archive Support

ZIP/CBZ is handled by the Python standard library. 7z/CB7 uses `py7zr` or external 7-Zip. RAR/CBR uses `rarfile`, or external 7z/7za/7zr, UnRAR, or bsdtar.

## License and Bundled Components

RAIV itself is released under the MIT License. See `LICENSE` for details.

Bundled external tools:

- Real-CUGAN ncnn Vulkan: MIT License  
  Included files: `tools\realcugan-ncnn-vulkan\LICENSE`, `tools\realcugan-ncnn-vulkan\README.md`
- Real-ESRGAN ncnn Vulkan / Real-ESRGAN: BSD 3-Clause License  
  Included files: `tools\realesrgan-ncnn-vulkan\LICENSE`, `tools\realesrgan-ncnn-vulkan\README_windows.md`

Topaz Gigapixel AI is not bundled. RAIV invokes a separately installed copy through its external CLI, subject to the product's own license.

When redistributing RAIV, keep the exe, DLL, model, README, and LICENSE files under `tools` intact.




