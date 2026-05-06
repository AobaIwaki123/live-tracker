# Routing & Glassmorphism

## 3D からのルーティング

`ArtistCard.tsx` (R3F コンポーネント) からの詳細ページへの遷移は、`react-router-dom` の `useNavigate` を利用します。

```tsx
import { useNavigate } from 'react-router-dom'

function ArtistCard({ artist }) {
  const navigate = useNavigate()
  
  return (
    <mesh onClick={() => navigate(`/artist/${artist.name}`)}>
      {/* ... */}
    </mesh>
  )
}
```
※注意: `useNavigate` を R3F Canvas 内で使用するためには、`<Canvas>` が `<Router>` の内側に配置されている必要があります。

## Glassmorphism (DOM UI)

3D の没入感を最大化するため、DOM レイヤーは極力背景色を排除します。

### Navbar
- `bg-white/70` などを `bg-black/20` や `bg-transparent` に変更。
- `backdrop-blur-md` で下の 3D オブジェクトを美しくぼかします。
- ボーダーも `border-white/10` などの微かなものにします。

### DetailPage
- 既存の `bg-card` (白/グレー) などを破棄し、ダークテーマベースの半透明パネル (`bg-slate-900/40 backdrop-blur-xl border border-white/10`) に変更します。
- ユーザーがアーティストの詳細を読んでいる間も、背景で宇宙空間がゆっくりと動いている状態を維持します。
