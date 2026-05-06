# R3F Immersive UI Architecture

## 全体構造 (Layering)

アプリケーションは、最背面の **3D Layer (Global Canvas)** と、その手前の **DOM Layer (React Router & UI)** の 2 層構造になります。

```
<body>
  <div id="root">
    {/* ── 3D Layer (Global) ── */}
    <GlobalCanvas />
    
    {/* ── DOM Layer (Routing & UI) ── */}
    <Router>
      <Navbar /> {/* グラスモーフィズムで背景を透過 */}
      <main className="transparent">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/artist/:id" element={<DetailPage />} />
        </Routes>
      </main>
    </Router>
  </div>
</body>
```

## Global Canvas の役割
- `App.tsx` のレベルでマウントされ、ページ遷移してもアンマウントされません。
- 宇宙空間の背景（Particles, Orbs, Rings）を常に描画します。
- `HomePage` でのみ、アーティストの 3D カード群 (`ArtistGrid`) を描画します。現在のルーティング状態を R3F 側に伝える工夫（例えば Zustand などの状態管理、または React Router の `useLocation` を Canvas 内で監視）が必要です。

## DOM Layer の役割
- `Navbar`: グラスモーフィズム（`backdrop-blur`）を適用し、下の 3D オブジェクトが透けて見えるようにします。
- `HomePage`: DOM としてのアーティストカードは描画せず、R3F 側に「HomePage にいること」を伝えます。DOM 側にはヒーローのテキスト（Live Tracker...）のみを配置します。
- `DetailPage`: 3D 背景の上に浮かび上がる、半透明な詳細パネルを描画します。

## 状態同期 (DOM ↔ 3D)
`@react-three/drei` の `<ScrollControls>` を DOM に依存させるか、あるいは 3D 内での独自のスクロール制御を行う必要があります。
今回は、ルーティングによって R3F 内の描画コンポーネント（ArtistGrid）の表示・非表示を切り替えるアプローチを取ります。
