# ビジュアル設計仕様

> `generate-og.html` の Three.js シーンをアニメーション対応した仕様として定義する。  
> 実装時はこのドキュメントを Single Source of Truth として参照すること。

---

## 1. カラーパレット

OG画像と完全一致させる。

| 役割 | 値 | 使用箇所 |
|------|-----|---------|
| 背景 | `#050010` | canvas 背景 / section CSS fallback |
| シーン背景 | `0x080012` | `scene.background` |
| 紫 (primary) | `#a855f7` / `0xa855f7` | パーティクル・リング・オーブ |
| 濃い紫 | `#7c3aed` / `0x7c3aed` | オーブ core・リング |
| ピンク | `#ec4899` / `0xec4899` | パーティクル・リング |
| 濃いピンク | `#db2777` / `0xdb2777` | オーブ |
| インディゴ | `#818cf8` / `0x818cf8` | パーティクル・リング |
| 深インディゴ | `#4338ca` / `0x4338ca` | オーブ |
| 薄紫 | `#9333ea` / `0x9333ea` | オーブ |
| ライトバイオレット | `#f0abfc` / `0xf0abfc` | パーティクル |
| 水色 | `#60a5fa` / `0x60a5fa` | パーティクル |
| 白 | `#ffffff` / `0xffffff` | パーティクル |

---

## 2. Three.js シーン構成

### カメラ

```
PerspectiveCamera
  fov:    60
  aspect: canvas.width / canvas.height（リサイズ時に更新）
  near:   0.1
  far:    100
  position: (0, 0, 7)
```

### レンダラー

```
WebGLRenderer
  antialias:    true
  alpha:        false
  toneMapping:  ACESFilmicToneMapping
  pixelRatio:   Math.min(devicePixelRatio, 2)
  size:         canvas の実サイズに追従（ResizeObserver）
```

---

## 3. シーンオブジェクト仕様

### 3-1. パーティクル

```
BufferGeometry / PointsMaterial
  COUNT:  500
  size:   0.07
  vertexColors: true
  transparent: true
  opacity: 0.85
  sizeAttenuation: true

初期配置:
  x: (Math.random() - 0.5) * 22
  y: (Math.random() - 0.5) * 12
  z: (Math.random() - 0.5) * 10 - 3  ← カメラ奥側に寄せる

カラー（パレットからランダムに 1 色割り当て）:
  #a855f7 / #ec4899 / #ffffff / #818cf8 / #f0abfc / #60a5fa

サイズ（各パーティクルへ個別割り当て）:
  Math.random() * 3 + 1  （1〜4 の範囲）
```

**アニメーション（OGからの追加）:**

```
毎フレーム: 各パーティクルの z を -0.002 ずつ減算（手前から奥へドリフト）
z が -8 を下回ったら z = +2 にリセット（無限ループ）
position attribute に needsUpdate = true をセット
```

---

### 3-2. グローイングオーブ（4個）

各オーブは haze（外側ぼかし）と core（中心輝点）の 2 メッシュで構成。

```
オーブ定義:
  { pos: [-2.5,  1.8, -2], color: 0x7c3aed, r: 1.4 }
  { pos: [ 3.5, -0.8, -1], color: 0xdb2777, r: 1.0 }
  { pos: [ 0.5, -2.8, -4], color: 0x4338ca, r: 1.8 }
  { pos: [-4.0, -1.5, -3], color: 0x9333ea, r: 0.8 }

haze:
  SphereGeometry(r, 32, 32)
  MeshBasicMaterial({ color, transparent: true, opacity: 0.12 })

core:
  SphereGeometry(r * 0.28, 16, 16)
  MeshBasicMaterial({ color, transparent: true, opacity: 0.7 })
```

**アニメーション（OGからの追加）:**

```
haze scale: 1.0 + Math.sin(elapsed * 0.8 + offset) * 0.08  （ゆっくりパルス）
core scale: 1.0 + Math.sin(elapsed * 1.2 + offset) * 0.12  （hazeより少し速い）
offset: オーブごとに異なる値 [0, π/2, π, 3π/2] を割り当て、同期しないようにする
```

---

### 3-3. トーラスリング（3個）

```
リング定義:
  { pos: [ 2.2,  0.3, -0.5], rx: 1.1, ry:  0.3, r: 1.9, tube: 0.04, color: 0xa855f7, op: 0.35, rz_speed:  0.003 }
  { pos: [-2.8, -0.4, -1  ], rx: 0.8, ry: -0.5, r: 1.4, tube: 0.03, color: 0xec4899, op: 0.28, rz_speed: -0.004 }
  { pos: [ 0.5,  2.0, -2  ], rx: 1.5, ry:  0.8, r: 2.2, tube: 0.035,color: 0x818cf8, op: 0.20, rz_speed:  0.002 }

TorusGeometry(r, tube, 16, 100)
MeshBasicMaterial({ color, transparent: true, opacity: op })
初期 rotation.x = rx, rotation.y = ry
```

**アニメーション（OGからの追加）:**

```
毎フレーム: mesh.rotation.z += rz_speed
（rx, ry は初期値のまま固定）
```

---

## 4. HTML テキストオーバーレイ仕様

Three.js canvas の上に `position: absolute` で HTML 要素を重ねる。

### レイアウト構造

```
ヒーローセクション全体: h-[420px] md:h-[380px] / relative / overflow-hidden
  ├── canvas（Three.js）: absolute inset-0 w-full h-full
  └── オーバーレイ div:   absolute inset-0 flex flex-col justify-center px-12 md:px-16
        ├── アプリアイコン （Music2 アイコン + グラデーション角丸正方形）
        ├── デコレーションライン（グラデーション hr 相当）
        ├── タイトル「Live Tracker」
        ├── サブタイトル「ライブ日程 追跡ツール」
        └── Feature chips（スケジュール自動取得 / Discord通知）
```

### テキストスタイル詳細

```
タイトル:
  font:     font-black text-5xl md:text-7xl tracking-tighter
  color:    bg-gradient-to-br from-white via-purple-200 to-violet-400 bg-clip-text text-transparent
  glow:     drop-shadow-[0_0_28px_rgba(167,139,250,0.6)]

サブタイトル:
  font:     font-normal text-xl md:text-2xl tracking-wide
  color:    text-violet-300/75

Feature chips:
  padding:  px-4 py-2
  bg:       bg-violet-900/40
  border:   border border-violet-400/30
  blur:     backdrop-blur-sm
  radius:   rounded-full
  text:     text-sm font-medium text-violet-200/90

デコレーションライン:
  CSS linear-gradient: from-violet-400/90 via-pink-500/60 to-transparent
  height: 2px, width: 300px〜460px
  box-shadow: 0 0 8px rgba(167,139,250,0.8)

アイコン:
  size:     w-16 h-16 (OGの 96px を比率換算)
  bg:       bg-gradient-to-br from-violet-700 to-purple-500
  radius:   rounded-2xl
  shadow:   shadow-lg shadow-purple-400/40
  icon:     Music2 (lucide-react), white, size=32
```

---

## 5. アニメーション仕様まとめ

| 要素 | アニメーション | 速度 |
|------|-------------|------|
| Particles | Z 方向ドリフト → 折り返し | 0.002/frame |
| Orbs (haze) | スケールパルス (sin波) | elapsed × 0.8 |
| Orbs (core) | スケールパルス (sin波) | elapsed × 1.2 |
| Rings | Z 軸自転 | 0.002〜0.004/frame（リングごとに異なる） |

全アニメーションは `requestAnimationFrame` ループで駆動する。  
ビューポート外（`IntersectionObserver`）ではループを停止してCPU・GPU負荷を下げる。

---

## 6. パフォーマンス考慮事項

| 項目 | 対策 |
|------|------|
| 高 DPI デバイス | `pixelRatio = Math.min(devicePixelRatio, 2)` |
| ウィンドウリサイズ | `ResizeObserver` で canvas サイズ・カメラ aspect を更新 |
| タブ非表示時 | `IntersectionObserver` でアニメーション停止 |
| アンマウント時 | `cancelAnimationFrame` + `renderer.dispose` + 全 geometry/material の `.dispose()` |
| パーティクル数 | OGと同じ 500 個（負荷が問題なければ増やさない） |
