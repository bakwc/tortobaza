"use client";

import { useEffect, useMemo, useRef } from "react";
import { useTexture } from "@react-three/drei";
import { ThreeEvent, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { cakeScriptFont } from "./cakeFont";
import {
  CAKE_RADIUS,
  DECORATION_Y,
  clampToCake,
  type Decoration,
  type ImageDecoration,
  type TextDecoration,
} from "./types";

type DecorationLayerProps = {
  decorations: Decoration[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onMove: (id: string, x: number, y: number) => void;
  onDragChange: (dragging: boolean) => void;
};

type MeshHandlers = {
  onPointerDown: (event: ThreeEvent<PointerEvent>) => void;
};

export function DecorationLayer({
  decorations,
  selectedId,
  onSelect,
  onMove,
  onDragChange,
}: DecorationLayerProps) {
  const { gl, camera } = useThree();
  const dragIdRef = useRef<string | null>(null);
  const onMoveRef = useRef(onMove);
  const onDragChangeRef = useRef(onDragChange);
  const onSelectRef = useRef(onSelect);
  onMoveRef.current = onMove;
  onDragChangeRef.current = onDragChange;
  onSelectRef.current = onSelect;

  const dragPlane = useMemo(
    () => new THREE.Plane(new THREE.Vector3(0, 1, 0), -DECORATION_Y),
    [],
  );

  useEffect(() => {
    const el = gl.domElement;
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const hit = new THREE.Vector3();

    function project(event: PointerEvent): [number, number] | null {
      const rect = el.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const ok = raycaster.ray.intersectPlane(dragPlane, hit);
      if (!ok) {
        return null;
      }
      return clampToCake(hit.x, hit.z);
    }

    function onPointerMove(event: PointerEvent) {
      if (!dragIdRef.current) {
        return;
      }
      const xy = project(event);
      if (!xy) {
        return;
      }
      onMoveRef.current(dragIdRef.current, xy[0], xy[1]);
    }

    function onPointerUp() {
      if (!dragIdRef.current) {
        return;
      }
      dragIdRef.current = null;
      onDragChangeRef.current(false);
    }

    el.addEventListener("pointermove", onPointerMove);
    el.addEventListener("pointerup", onPointerUp);
    el.addEventListener("pointercancel", onPointerUp);
    return () => {
      el.removeEventListener("pointermove", onPointerMove);
      el.removeEventListener("pointerup", onPointerUp);
      el.removeEventListener("pointercancel", onPointerUp);
    };
  }, [gl, camera, dragPlane]);

  function beginDrag(id: string, event: ThreeEvent<PointerEvent>) {
    event.stopPropagation();
    dragIdRef.current = id;
    onSelectRef.current(id);
    onDragChangeRef.current(true);
  }

  return (
    <group>
      <mesh
        position={[0, DECORATION_Y, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        onPointerDown={(event) => {
          if (dragIdRef.current) {
            return;
          }
          event.stopPropagation();
          onSelectRef.current(null);
        }}
      >
        <circleGeometry args={[CAKE_RADIUS, 64]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      {decorations.map((decoration) =>
        decoration.kind === "text" ? (
          <TextDecorationMesh
            key={decoration.id}
            decoration={decoration}
            selected={decoration.id === selectedId}
            onPointerDown={(event) => beginDrag(decoration.id, event)}
          />
        ) : (
          <ImageDecorationMesh
            key={decoration.id}
            decoration={decoration}
            selected={decoration.id === selectedId}
            onPointerDown={(event) => beginDrag(decoration.id, event)}
          />
        ),
      )}
    </group>
  );
}

function buildTextTexture(text: string): {
  texture: THREE.CanvasTexture;
  width: number;
  height: number;
} {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("2d context unavailable");
  }
  const fontSize = 96;
  const font = `700 ${fontSize}px ${cakeScriptFont.style.fontFamily}, "Jost", "Montserrat", cursive`;
  ctx.font = font;
  const lines = (text.length > 0 ? text : " ").split("\n");
  const metrics = lines.map((line) => ctx.measureText(line));
  const textWidth = Math.max(...metrics.map((m) => m.width), 32);
  const lineHeight = fontSize * 1.2;
  const pad = 48;
  canvas.width = Math.ceil(textWidth + pad * 2);
  canvas.height = Math.ceil(lineHeight * lines.length + pad * 2);
  ctx.font = font;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "#1a1a1a";
  lines.forEach((line, index) => {
    const y = pad + lineHeight * (index + 0.5);
    ctx.fillText(line, canvas.width / 2, y);
  });
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  const worldHeight = 0.28;
  const aspect = canvas.width / canvas.height;
  return {
    texture,
    width: worldHeight * aspect,
    height: worldHeight,
  };
}

function TextDecorationMesh({
  decoration,
  selected,
  onPointerDown,
}: {
  decoration: TextDecoration;
  selected: boolean;
} & MeshHandlers) {
  const drawn = useMemo(() => buildTextTexture(decoration.text), [decoration.text]);

  useEffect(() => {
    return () => {
      drawn.texture.dispose();
    };
  }, [drawn]);

  const width = drawn.width * decoration.scale;
  const height = drawn.height * decoration.scale;

  return (
    <group position={[decoration.x, DECORATION_Y + 0.002, decoration.y]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} onPointerDown={onPointerDown}>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial map={drawn.texture} transparent toneMapped={false} />
      </mesh>
      {selected ? (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.001, 0]}>
          <ringGeometry
            args={[Math.max(width, height) * 0.55, Math.max(width, height) * 0.62, 32]}
          />
          <meshBasicMaterial color="#cc767f" transparent opacity={0.7} />
        </mesh>
      ) : null}
    </group>
  );
}

function ImageDecorationMesh({
  decoration,
  selected,
  onPointerDown,
}: {
  decoration: ImageDecoration;
  selected: boolean;
} & MeshHandlers) {
  const texture = useTexture(decoration.src);
  texture.colorSpace = THREE.SRGBColorSpace;
  const size = 0.55 * decoration.scale;

  return (
    <group position={[decoration.x, DECORATION_Y + 0.002, decoration.y]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} onPointerDown={onPointerDown}>
        <planeGeometry args={[size, size]} />
        <meshBasicMaterial map={texture} transparent toneMapped={false} />
      </mesh>
      {selected ? (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.001, 0]}>
          <ringGeometry args={[size * 0.55, size * 0.62, 32]} />
          <meshBasicMaterial color="#cc767f" transparent opacity={0.7} />
        </mesh>
      ) : null}
    </group>
  );
}
