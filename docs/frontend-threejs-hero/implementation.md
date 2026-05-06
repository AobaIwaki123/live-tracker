# 実装手順・チェックリスト

> Three.js ヒーローセクションの実装を確実に行うためのガイド。

---

## 1. 準備

### 依存パッケージのインストール
```bash
cd frontend
npm install three
npm install -D @types/three
```

---

## 2. フェーズ 1: Hooks & コンポーネント作成

1.  **`frontend/src/components/three/useThreeScene.ts` の作成**
    - [hooks.md](./hooks.md) のコードを実装する。
    - パーティクル、オーブ、リングのアニメーションロジックが正しくループしていることを確認。
    - クリーンアップ（dispose）が漏れていないかチェック。

2.  **`frontend/src/components/three/HeroCanvas.tsx` の作成**
    - [components.md](./components.md) の DOM 構造を実装する。
    - Tailwind CSS でのスタイリング、グラデーション、drop-shadow を適用する。
    - `pointer-events-none` がオーバーレイ要素に付いていることを確認。

---

## 3. フェーズ 2: ページへの組み込み

1.  **`frontend/src/pages/HomePage.tsx` の修正**
    - `HeroCanvas` をインポート。
    - `isLoading` や `error` の状態に関わらずヒーローセクションが表示されるように配置を調整する（オプション）。
    - 既存の「アーティスト」タイトルのマージンを調整し、ヒーローセクションとの繋がりを自然にする。

---

## 4. 完了チェックリスト

- [ ] `three` パッケージが `package.json` に追加されている
- [ ] 画面リサイズ時に Canvas のアスペクト比が正しく更新される
- [ ] ブラウザのタブを切り替えた際、またはスクロールして画面外に出た際にアニメーションが停止する（IntersectionObserver）
- [ ] コンポーネントのアンマウント時にコンソールエラーが出ない（クリーンアップの確認）
- [ ] モバイル端末（レスポンシブ）でテキストがはみ出さない
- [ ] ダークモード以外の設定でも背景色が `#050010` で固定されている（サイト全体の方針と一致）

---

## 5. トラブルシューティング

- **Canvas が表示されない**: `HeroCanvas.tsx` の親要素や Canvas 自体に `height` が設定されているか確認してください。
- **パーティクルが動かない**: `useThreeScene.ts` 内の `animate` 関数が正しく呼び出されているか、`isVisible` が `true` になっているか確認してください。
- **重い**: `pixelRatio` を `Math.min(window.devicePixelRatio, 2)` に制限しているか確認してください。
