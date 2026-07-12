"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { ContactShadows, OrbitControls } from "@react-three/drei";
import { TOUCH } from "three";
import { CakeModel } from "./CakeModel";
import { DecorationLayer } from "./DecorationLayer";
import { BOARD_HEIGHT, type Decoration } from "./types";

type CakeSceneProps = {
  decorations: Decoration[];
  selectedId: string | null;
  isDragging: boolean;
  onSelect: (id: string | null) => void;
  onMove: (id: string, x: number, y: number) => void;
  onDragChange: (dragging: boolean) => void;
};

export default function CakeScene({
  decorations,
  selectedId,
  isDragging,
  onSelect,
  onMove,
  onDragChange,
}: CakeSceneProps) {
  return (
    <Canvas
      className="h-full w-full touch-none"
      camera={{ position: [2.6, 2.9, 2.6], fov: 35, near: 0.1, far: 50 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
    >
      <color attach="background" args={["#f4ece3"]} />
      <ambientLight intensity={0.75} />
      <directionalLight
        castShadow
        position={[4, 8, 3]}
        intensity={1.15}
        shadow-mapSize={[1024, 1024]}
      />
      <directionalLight position={[-3, 4, -2]} intensity={0.35} />
      <Suspense fallback={null}>
        <CakeModel />
        <DecorationLayer
          decorations={decorations}
          selectedId={selectedId}
          onSelect={onSelect}
          onMove={onMove}
          onDragChange={onDragChange}
        />
      </Suspense>
      <ContactShadows
        position={[0, -BOARD_HEIGHT, 0]}
        opacity={0.4}
        scale={8}
        blur={2.4}
        far={4}
      />
      <OrbitControls
        makeDefault
        enablePan={false}
        enabled={!isDragging}
        minPolarAngle={Math.PI / 5}
        maxPolarAngle={Math.PI / 2.15}
        minDistance={3}
        maxDistance={9}
        target={[0, 0.35, 0]}
        touches={{ ONE: TOUCH.ROTATE, TWO: TOUCH.DOLLY_PAN }}
      />
    </Canvas>
  );
}
