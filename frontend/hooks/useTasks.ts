"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { TaskBody, TaskCommentBody } from "@/lib/api/types";

const key = ["tasks"] as const;

export function useTasks(hideOldDone: boolean) {
  const qc = useQueryClient();
  const list = useQuery({
    queryKey: [...key, hideOldDone],
    queryFn: () => api.tasks.list(hideOldDone),
  });
  const assignees = useQuery({
    queryKey: ["task-assignees"],
    queryFn: () => api.taskAssignees.list(),
  });
  const save = useMutation({
    mutationFn: ({ id, body }: { id: number | null; body: TaskBody }) =>
      id === null ? api.tasks.create(body) : api.tasks.update(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.tasks.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  const saveComment = useMutation({
    mutationFn: ({
      taskId,
      commentId,
      body,
    }: {
      taskId: number;
      commentId: number | null;
      body: TaskCommentBody;
    }) =>
      commentId === null
        ? api.tasks.createComment(taskId, body)
        : api.tasks.updateComment(taskId, commentId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  const removeComment = useMutation({
    mutationFn: ({ taskId, commentId }: { taskId: number; commentId: number }) =>
      api.tasks.removeComment(taskId, commentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  return { list, assignees, save, remove, saveComment, removeComment };
}
