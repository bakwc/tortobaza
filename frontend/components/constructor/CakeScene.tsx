"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { TOUCH } from "three";
import { CakeModel } from "./CakeModel";
import { DecorationLayer } from "./DecorationLayer";
import { BOARD_HEIGHT, BOARD_RADIUS, CAKE_HEIGHT, type Decoration } from "./types";

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
      camera={{ position: [0.75, 4.0, 2.85], fov: 28, near: 0.1, far: 50 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: false, toneMappingExposure: 1.15 }}
      flat
    >
      <color attach="background" args={["#efe5db"]} />
      <ambientLight intensity={1.4} color="#ffffff" />
      <directionalLight position={[-2.5, 6, 2]} intensity={1.2} color="#fffaf3" />
      <directionalLight position={[3, 1.5, -2]} intensity={0.3} color="#e8dccf" />
      <hemisphereLight args={["#ffffff", "#e0d2c2", 0.4]} />
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0.28, -BOARD_HEIGHT - 0.004, 0.22]}
        scale={[1.25, 1.1, 1]}
      >
        <circleGeometry args={[BOARD_RADIUS * 0.95, 64]} />
        <meshBasicMaterial color="#b7aa98" transparent opacity={0.16} />
      </mesh>
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
      <OrbitControls
        makeDefault
        enablePan={false}
        enabled={!isDragging}
        minPolarAngle={Math.PI / 8}
        maxPolarAngle={Math.PI / 2.2}
        minDistance={3.2}
        maxDistance={9}
        target={[0, CAKE_HEIGHT * 0.3, 0]}
        touches={{ ONE: TOUCH.ROTATE, TWO: TOUCH.DOLLY_PAN }}
      />
    </Canvas>
  );
}
