"use client";

import {
  BlockTypeSelect,
  BoldItalicUnderlineToggles,
  DiffSourceToggleWrapper,
  InsertTable,
  ListsToggle,
  MDXEditor,
  Separator,
  UndoRedo,
  diffSourcePlugin,
  headingsPlugin,
  listsPlugin,
  markdownShortcutPlugin,
  quotePlugin,
  tablePlugin,
  thematicBreakPlugin,
  toolbarPlugin,
} from "@mdxeditor/editor";
import "@mdxeditor/editor/style.css";

const plugins = [
  headingsPlugin({ allowedHeadingLevels: [2, 3, 4] }),
  listsPlugin(),
  quotePlugin(),
  thematicBreakPlugin(),
  tablePlugin(),
  markdownShortcutPlugin(),
  diffSourcePlugin({ viewMode: "rich-text" }),
  toolbarPlugin({
    toolbarContents: () => (
      <DiffSourceToggleWrapper options={["rich-text", "source"]}>
        <UndoRedo />
        <Separator />
        <BlockTypeSelect />
        <BoldItalicUnderlineToggles />
        <ListsToggle options={["bullet", "number"]} />
        <InsertTable />
      </DiffSourceToggleWrapper>
    ),
  }),
];

export default function MarkdownEditorField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
      <MDXEditor
        markdown={value}
        onChange={(markdown, initialMarkdownNormalize) => {
          if (!initialMarkdownNormalize) onChange(markdown);
        }}
        plugins={plugins}
        contentEditableClassName="min-h-48 px-3 py-2 text-sm leading-6 text-[var(--ink)] [&_h2]:mt-5 [&_h2]:text-base [&_h2]:font-semibold [&_h2:first-child]:mt-0 [&_h3]:mt-4 [&_h3]:font-semibold [&_h3:first-child]:mt-0 [&_h4]:mt-3 [&_h4]:font-medium [&_h4:first-child]:mt-0"
      />
    </div>
  );
}
