"use client";

import { BOARD_HEIGHT, BOARD_RADIUS, CAKE_HEIGHT, CAKE_RADIUS } from "./types";

const FROSTING = "#f7f2ea";
const BOARD = "#ffffff";

export function CakeModel() {
  return (
    <group>
      <mesh position={[0, -BOARD_HEIGHT / 2, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[BOARD_RADIUS, BOARD_RADIUS, BOARD_HEIGHT, 64]} />
        <meshStandardMaterial color={BOARD} roughness={0.55} metalness={0.05} />
      </mesh>
      <mesh position={[0, CAKE_HEIGHT / 2, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[CAKE_RADIUS, CAKE_RADIUS, CAKE_HEIGHT, 64]} />
        <meshStandardMaterial color={FROSTING} roughness={0.85} metalness={0} />
      </mesh>
    </group>
  );
}
