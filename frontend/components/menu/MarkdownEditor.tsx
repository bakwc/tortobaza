"use client";

import dynamic from "next/dynamic";

export const MarkdownEditor = dynamic(() => import("./MarkdownEditorField"), { ssr: false });
