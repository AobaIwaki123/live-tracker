# Three.js Hero セクション — 概要

> **対象**: `frontend/src/components/three/` + `frontend/src/pages/HomePage.tsx`  
> **ステータス**: 設計レビュー完了・実装準備OK  
> **参照元ビジュアル**: `frontend/generate-og.html`（OG画像生成スクリプト）

---

## 何をするか

HomePage の最上部に Three.js 製のアニメーション背景を持つヒーローセクションを追加する。  
`generate-og.html` で生成した `og.png` と同一の世界観（深宇宙紫 × パーティクル × オーブ × リング）を、静止画ではなくリアルタイムアニメーションとして実装する。

### Before / After

```
【Before】
Navbar
└── アーティストグリッド

【After】
Navbar
└── HeroCanvas（Three.js アニメーション + HTML テキストオーバーレイ）
└── アーティストグリッド（変更なし）
```

---

## ドキュメント構成

| ファイル | 内容 |
|---------|------|
| **README.md**（本ファイル） | 概要・背景・ドキュメントマップ |
| [visual-design.md](./visual-design.md) | カラー・Three.js シーン構成・アニメーション仕様 |
| [components.md](./components.md) | コンポーネント設計・Props・DOM構造・CSS |
| [hooks.md](./hooks.md) | `useThreeScene` フック仕様（初期化・ループ・クリーンアップ） |
| [implementation.md](./implementation.md) | 実装手順・コマンド・完了チェックリスト |

**読む順序**: README → visual-design → components → hooks → implementation

---

## 設計の核となる判断

### なぜ vanilla Three.js か（React Three Fiber を使わない理由）

`generate-og.html` の Three.js コードは vanilla で書かれており、フロントに組み込む際も同じコードベースを転用できる。R3F は React との統合が綺麗だが、バンドルサイズが増加し、OGコードからの移植コストも高い。シーンの複雑度（パーティクル×1 + オーブ×4 + リング×3）は vanilla で十分管理可能。

### なぜ HTML/CSS テキストか（Canvas 2D テキストを使わない理由）

OG画像生成では Canvas 2D でテキストを描く必要があった（静止画として書き出すため）。フロントページでは HTML テキストの方がレスポンシブ対応・アクセシビリティ・フォント読み込みタイミングで優位。グロー効果は CSS `text-shadow` / `drop-shadow` で十分再現できる。

### なぜライトモードを考慮しないか

本プロジェクトのフロントエンドはダークモード前提で運用する方針。ヒーローセクションの背景 `#050010` はサイト全体と独立した暗色領域として成立するため、ライトモード切り替えのサポートは不要。

---

## 依存パッケージ

```bash
# 追加するもの
npm install three @types/three

# 既存（変更なし）
react, react-dom, tailwindcss, lucide-react
```

`three` のバンドルサイズ: 非圧縮 ~580KB、gzip後 ~170KB（許容範囲）。

---

## 影響範囲

| ファイル | 変更種別 |
|---------|---------|
| `frontend/package.json` | `three` / `@types/three` 追加 |
| `frontend/src/components/three/useThreeScene.ts` | 新規作成 |
| `frontend/src/components/three/HeroCanvas.tsx` | 新規作成 |
| `frontend/src/pages/HomePage.tsx` | `<HeroCanvas />` を先頭に挿入（既存部分変更なし） |

バックエンド・APIへの変更は一切ない。
