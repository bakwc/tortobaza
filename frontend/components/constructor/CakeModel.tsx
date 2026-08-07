"use client";

import { BOARD_HEIGHT, BOARD_RADIUS, CAKE_HEIGHT, CAKE_RADIUS } from "./types";

const FROSTING = "#f7efe0";
const BOARD = "#faf6f0";

export function CakeModel() {
  return (
    <group>
      <mesh position={[0, -BOARD_HEIGHT / 2, 0]} receiveShadow>
        <cylinderGeometry args={[BOARD_RADIUS, BOARD_RADIUS, BOARD_HEIGHT, 96]} />
        <meshStandardMaterial color={BOARD} roughness={0.65} metalness={0} />
      </mesh>
      <mesh position={[0, CAKE_HEIGHT / 2, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[CAKE_RADIUS, CAKE_RADIUS, CAKE_HEIGHT, 96]} />
        <meshStandardMaterial color={FROSTING} roughness={0.95} metalness={0} />
      </mesh>
    </group>
  );
}
