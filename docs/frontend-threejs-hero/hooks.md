# useThreeScene フック仕様

> Three.js のライフサイクル全体を管理するカスタムフック。  
> シーン構築・アニメーションループ・クリーンアップを完全にカプセル化する。

---

## シグネチャ

```typescript
export function useThreeScene(canvasRef: RefObject<HTMLCanvasElement>): void
```

**引数:** Three.js がレンダリング先として使う `<canvas>` の ref  
**返値:** なし（副作用のみ）

---

## 全体構造

```typescript
export function useThreeScene(canvasRef: RefObject<HTMLCanvasElement>): void {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // 1. Three.js 初期化（renderer, scene, camera）
    // 2. シーンオブジェクト構築（particles, orbs, rings）
    // 3. ResizeObserver 登録
    // 4. IntersectionObserver 登録
    // 5. アニメーションループ開始
    // 6. クリーンアップ関数を返す

    return () => {
      // cancelAnimationFrame
      // ResizeObserver.disconnect
      // IntersectionObserver.disconnect
      // renderer.dispose + 全リソース dispose
    };
  }, []);  // マウント時のみ実行（canvasRef は安定しているため deps 不要）
}
```

---

## 1. Three.js 初期化

```typescript
const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: false,
});
renderer.setSize(canvas.clientWidth, canvas.clientHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x080012);

const camera = new THREE.PerspectiveCamera(
  60,
  canvas.clientWidth / canvas.clientHeight,
  0.1,
  100
);
camera.position.set(0, 0, 7);
```

---

## 2. シーンオブジェクト構築

### 2-1. パーティクル

```typescript
const PARTICLE_COUNT = 500;
const positions = new Float32Array(PARTICLE_COUNT * 3);
const colors    = new Float32Array(PARTICLE_COUNT * 3);
const sizes     = new Float32Array(PARTICLE_COUNT);

const palette = [
  new THREE.Color(0xa855f7),
  new THREE.Color(0xec4899),
  new THREE.Color(0xffffff),
  new THREE.Color(0x818cf8),
  new THREE.Color(0xf0abfc),
  new THREE.Color(0x60a5fa),
];

for (let i = 0; i < PARTICLE_COUNT; i++) {
  positions[i * 3]     = (Math.random() - 0.5) * 22;
  positions[i * 3 + 1] = (Math.random() - 0.5) * 12;
  positions[i * 3 + 2] = (Math.random() - 0.5) * 10 - 3;
  const c = palette[Math.floor(Math.random() * palette.length)];
  colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
  sizes[i] = Math.random() * 3 + 1;
}

const particleGeo = new THREE.BufferGeometry();
particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
particleGeo.setAttribute('color',    new THREE.BufferAttribute(colors,    3));
particleGeo.setAttribute('size',     new THREE.BufferAttribute(sizes,     1));

const particleMat = new THREE.PointsMaterial({
  size: 0.07,
  vertexColors: true,
  transparent: true,
  opacity: 0.85,
  sizeAttenuation: true,
});
const particles = new THREE.Points(particleGeo, particleMat);
scene.add(particles);
```

### 2-2. グローイングオーブ

```typescript
// ref を保持してアニメーションで参照する
const hazes: THREE.Mesh[] = [];
const cores: THREE.Mesh[] = [];

const ORB_DEFS = [
  { pos: [-2.5,  1.8, -2] as const, color: 0x7c3aed, r: 1.4 },
  { pos: [ 3.5, -0.8, -1] as const, color: 0xdb2777, r: 1.0 },
  { pos: [ 0.5, -2.8, -4] as const, color: 0x4338ca, r: 1.8 },
  { pos: [-4.0, -1.5, -3] as const, color: 0x9333ea, r: 0.8 },
];

ORB_DEFS.forEach(({ pos, color, r }) => {
  const haze = new THREE.Mesh(
    new THREE.SphereGeometry(r, 32, 32),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.12 })
  );
  haze.position.set(...pos);
  scene.add(haze);
  hazes.push(haze);

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(r * 0.28, 16, 16),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.7 })
  );
  core.position.set(...pos);
  scene.add(core);
  cores.push(core);
});
```

### 2-3. トーラスリング

```typescript
const RING_DEFS = [
  { pos: [ 2.2,  0.3, -0.5] as const, rx: 1.1, ry:  0.3, r: 1.9, tube: 0.04,  color: 0xa855f7, op: 0.35, rzSpeed:  0.003 },
  { pos: [-2.8, -0.4, -1  ] as const, rx: 0.8, ry: -0.5, r: 1.4, tube: 0.03,  color: 0xec4899, op: 0.28, rzSpeed: -0.004 },
  { pos: [ 0.5,  2.0, -2  ] as const, rx: 1.5, ry:  0.8, r: 2.2, tube: 0.035, color: 0x818cf8, op: 0.20, rzSpeed:  0.002 },
];

const rings: Array<{ mesh: THREE.Mesh; rzSpeed: number }> = [];

RING_DEFS.forEach(({ pos, rx, ry, r, tube, color, op, rzSpeed }) => {
  const mesh = new THREE.Mesh(
    new THREE.TorusGeometry(r, tube, 16, 100),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: op })
  );
  mesh.rotation.x = rx;
  mesh.rotation.y = ry;
  mesh.position.set(...pos);
  scene.add(mesh);
  rings.push({ mesh, rzSpeed });
});
```

---

## 3. ResizeObserver

canvas サイズが変わったときにレンダラーとカメラを更新する。

```typescript
const resizeObserver = new ResizeObserver(() => {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  renderer.setSize(w, h, false);  // false: CSS サイズは変更しない
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
});
resizeObserver.observe(canvas);
```

---

## 4. IntersectionObserver

ヒーローが画面外に出たらアニメーションを停止し、GPU 負荷を下げる。

```typescript
let isVisible = true;

const intersectionObserver = new IntersectionObserver(
  ([entry]) => { isVisible = entry.isIntersecting; },
  { threshold: 0 }
);
intersectionObserver.observe(canvas);
```

---

## 5. アニメーションループ

```typescript
let animFrameId: number;
const clock = new THREE.Clock();

function animate() {
  animFrameId = requestAnimationFrame(animate);
  if (!isVisible) return;  // ビューポート外はスキップ

  const delta = clock.getDelta();
  const elapsed = clock.getElapsedTime();

  // ── Particles: Z ドリフト ──
  // 60fps (1/60 = 0.016s) で 0.002 移動させる = 秒速 0.12
  const pos = particleGeo.attributes.position.array as Float32Array;
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    pos[i * 3 + 2] -= 0.12 * delta;
    if (pos[i * 3 + 2] < -8) pos[i * 3 + 2] = 2;
  }
  particleGeo.attributes.position.needsUpdate = true;

  // ── Orbs: スケールパルス ──
  const phaseOffsets = [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2];
  hazes.forEach((haze, i) => {
    const s = 1.0 + Math.sin(elapsed * 0.8 + phaseOffsets[i]) * 0.08;
    haze.scale.setScalar(s);
  });
  cores.forEach((core, i) => {
    const s = 1.0 + Math.sin(elapsed * 1.2 + phaseOffsets[i]) * 0.12;
    core.scale.setScalar(s);
  });

  // ── Rings: Z 軸自転 ──
  // 60fps で 0.002〜0.004 回転 = 秒速 0.12〜0.24
  rings.forEach(({ mesh, rzSpeed }) => {
    mesh.rotation.z += (rzSpeed * 60) * delta;
  });

  renderer.render(scene, camera);
}

animate();
```

---

## 6. クリーンアップ

```typescript
return () => {
  cancelAnimationFrame(animFrameId);
  resizeObserver.disconnect();
  intersectionObserver.disconnect();

  // Three.js リソースを明示的に解放
  particleGeo.dispose();
  particleMat.dispose();

  [...hazes, ...cores].forEach((mesh) => {
    mesh.geometry.dispose();
    (mesh.material as THREE.Material).dispose();
  });

  rings.forEach(({ mesh }) => {
    mesh.geometry.dispose();
    (mesh.material as THREE.Material).dispose();
  });

  renderer.dispose();
};
```

---

## 型インポート

```typescript
import { useEffect, type RefObject } from "react";
import * as THREE from "three";
```

---

## よくある落とし穴

| 問題 | 原因 | 対策 |
|------|------|------|
| canvas が真っ黒 | canvas の clientWidth/Height が 0 | CSS で `width: 100%; height: 100%` を確実に設定してから初期化 |
| リサイズで歪む | `renderer.setSize(w, h)` のみ更新し `camera.aspect` を忘れた | ResizeObserver 内で必ず両方を更新 |
| メモリリーク | アンマウント時に `dispose` を呼び忘れ | クリーンアップ関数に全 geometry/material/renderer を列挙する |
| TS エラー: `pos[i * 3 + 2]` | `BufferAttribute.array` が `ArrayLike<number>` 型 | `as Float32Array` でキャスト |
| フォント未適用 | Canvas 2D でのテキスト描画時にフォントが読み込まれていない | HTML テキストを使うので本実装では不問 |
