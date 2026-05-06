# コンポーネント設計仕様

> 新規作成するファイルの構造・Props・DOM構造・責務を定義する。

---

## ファイル構成

```
frontend/src/components/three/
├── useThreeScene.ts   # Three.js ライフサイクル管理 hook（詳細は hooks.md）
└── HeroCanvas.tsx     # ヒーローセクション UI コンポーネント
```

---

## HeroCanvas.tsx

### 責務

- `<canvas>` を配置し `useThreeScene` hook に渡す
- Three.js canvas の上に HTML テキストオーバーレイを重ねる
- セクション全体のサイズ・背景色を管理する
- props は持たない（自己完結）

### シグネチャ

```typescript
export default function HeroCanvas(): React.JSX.Element
```

props なし。

### DOM 構造

```tsx
<section
  className="relative overflow-hidden"
  style={{ height: "420px", background: "#050010" }}
  // height は Tailwind クラスで: h-[420px] md:h-[380px]
>
  {/* ── Layer 1: Three.js canvas ── */}
  <canvas
    ref={canvasRef}
    className="absolute inset-0 w-full h-full"
  />

  {/* ── Layer 2: HTML テキストオーバーレイ ── */}
  <div className="absolute inset-0 flex flex-col justify-center px-12 md:px-16 pointer-events-none">

    {/* アイコン */}
    <div className="flex h-16 w-16 items-center justify-center rounded-2xl
                    bg-gradient-to-br from-violet-700 to-purple-500
                    shadow-lg shadow-purple-400/40 mb-6">
      <Music2 className="h-8 w-8 text-white" />
    </div>

    {/* デコレーションライン */}
    <div className="h-px w-[360px] mb-4"
         style={{
           background: "linear-gradient(to right, rgba(167,139,250,0.9), rgba(236,72,153,0.6), transparent)",
           boxShadow: "0 0 8px rgba(167,139,250,0.8)"
         }}
    />

    {/* タイトル */}
    <h2 className="font-black text-5xl md:text-7xl tracking-tighter
                   bg-gradient-to-br from-white via-purple-200 to-violet-400
                   bg-clip-text text-transparent
                   drop-shadow-[0_0_28px_rgba(167,139,250,0.6)]
                   mb-3">
      Live Tracker
    </h2>

    {/* サブタイトル */}
    <p className="text-xl md:text-2xl font-normal tracking-wide text-violet-300/75 mb-6">
      ライブ日程 追跡ツール
    </p>

    {/* Feature chips */}
    <div className="flex gap-3 flex-wrap">
      {["スケジュール自動取得", "Discord 通知"].map((label) => (
        <span
          key={label}
          className="px-4 py-2 rounded-full text-sm font-medium text-violet-200/90
                     bg-violet-900/40 border border-violet-400/30 backdrop-blur-sm"
        >
          {label}
        </span>
      ))}
    </div>
  </div>
</section>
```

### 注意点

- `<h2>` を使う（`<h1>` はページタイトル「アーティスト」が担うため）
- オーバーレイ div に `pointer-events-none` を付ける（Three.js canvas のマウスイベントを妨げないため）
- `background: "#050010"` は CSS に直書きする（Three.js がロードされる前のフォールバック色）
- `useThreeScene` に渡す `canvasRef` の型は `RefObject<HTMLCanvasElement>`

---

## useThreeScene.ts

詳細は [hooks.md](./hooks.md) を参照。

### シグネチャ（概要のみ）

```typescript
export function useThreeScene(canvasRef: RefObject<HTMLCanvasElement>): void
```

返値なし。副作用のみ（マウント時に Three.js を初期化し、アンマウント時にすべてクリーンアップする）。

---

## HomePage.tsx の変更点

### 変更内容

既存コードの先頭に `<HeroCanvas />` を挿入する。  
**注意**: `isLoading` や `error` による早期リターンの「外側」に配置することで、データの読み込み状況に関わらずヒーローセクションを即座に表示させる。

```tsx
export default function HomePage() {
  const { data: artists, isLoading, error } = useArtists();

  // 1. 共通のラッパーを返す
  return (
    <>
      <HeroCanvas />
      
      {/* 2. 状態に応じたコンテンツの切り替え */}
      {isLoading ? (
        <div className="mx-auto max-w-5xl px-4 py-12">
          {/* Skeleton 表示 */}
        </div>
      ) : error ? (
        <div className="mx-auto max-w-3xl px-4 py-24 text-center">
          {/* エラー表示 */}
        </div>
      ) : (
        <div className="mx-auto max-w-5xl px-4 py-12">
          <header className="mb-12 text-center">
             <h1 className="...">アーティスト</h1>
          </header>
          <div className="grid ...">
            {/* アーティスト一覧 */}
          </div>
        </div>
      )}
    </>
  );
}
```

`<HeroCanvas />` は `max-w-5xl` の外側（全幅）に配置する。  
既存のコンテンツは条件分岐（三項演算子など）で制御するようにリファクタリングする。

### import 追加

```typescript
import HeroCanvas from "@/components/three/HeroCanvas";
```

---

## コンポーネント依存関係図

```
HomePage
└── HeroCanvas
      ├── useThreeScene  （Three.js ライフサイクル）
      └── Music2         （lucide-react、既存 dep）
```

Three.js 固有のロジックは `useThreeScene` に完全に閉じ込めること。  
`HeroCanvas` は pure な UI コンポーネントとして、Three.js を直接触らない。
