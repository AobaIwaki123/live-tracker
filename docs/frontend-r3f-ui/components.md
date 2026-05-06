# R3F Components Design

## ファイル構成

```
src/components/r3f/
├── GlobalCanvas.tsx    # R3F <Canvas> のルート。全体の設定を管理
├── Background.tsx      # 宇宙の背景（Particles, Orbs, Rings を統括）
│   ├── Particles.tsx
│   ├── Orbs.tsx
│   └── Rings.tsx
└── ArtistGrid.tsx      # 3D 空間上のアーティスト一覧
    └── ArtistCard.tsx  # 個別の 3D カード
```

## コンポーネント詳細

### `GlobalCanvas`
- `Canvas` のセットアップ（FOV: 60, camera position: [0, 0, 7]）。
- `colorManagement`, `toneMapping` などを適切に設定。

### `Background` (Particles, Orbs, Rings)
- Vanilla Three.js で使用していたロジックを `useFrame` フックを用いた宣言的アニメーションに書き換えます。
- `delta` タイムを用いて、リフレッシュレートに依存しない等速アニメーションを実装します。

### `ArtistGrid` & `ArtistCard`
- `HomePage` 表示時のみマウントされます。
- `useArtists` フック（DOM 側と同じもの）からデータを取得、または props として受け取ります。
- `ArtistCard` は `@react-three/drei` の `<Image>` を利用してアーティストの画像を板ポリゴンとして表示し、下に `<Text>` で名前を描画します。
- `onPointerOver`, `onPointerOut` イベントで 3D 的なホバーエフェクト（スケールアップやわずかな Z 軸移動）を実装します。
