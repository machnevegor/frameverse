import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createTask, presign, uploadToS3 } from "#/shared/api/client";
import type { CreateTaskInput, PresignData } from "#/shared/api/types";

export interface UploadState {
  videoProgress: number;
  posterProgress: number;
  stage:
    | "idle"
    | "presign"
    | "uploading-video"
    | "uploading-poster"
    | "creating"
    | "done";
}

interface UploadMovieParams {
  videoFile: File;
  posterFile?: File | null;
  metadata: Omit<CreateTaskInput, "s3_key" | "poster_s3_key">;
  onProgress?: (state: UploadState) => void;
}

// Full upload flow: presign → upload video → (presign + upload poster) → createTask
export async function uploadMovie(
  params: UploadMovieParams,
): Promise<{ taskId: string }> {
  const { videoFile, posterFile, metadata, onProgress } = params;
  const report = (
    state: Partial<UploadState> & { stage: UploadState["stage"] },
  ) => {
    onProgress?.({
      videoProgress: 0,
      posterProgress: 0,
      ...state,
    } as UploadState);
  };

  report({ stage: "presign", videoProgress: 0, posterProgress: 0 });

  const videoPresign: PresignData = await presign({
    content_type: videoFile.type,
  });

  report({ stage: "uploading-video", videoProgress: 0, posterProgress: 0 });
  await uploadToS3(videoPresign.upload_url, videoFile, (pct) => {
    report({ stage: "uploading-video", videoProgress: pct, posterProgress: 0 });
  });

  let posterS3Key: string | null = null;
  if (posterFile) {
    report({
      stage: "uploading-poster",
      videoProgress: 100,
      posterProgress: 0,
    });
    const posterPresign = await presign({ content_type: posterFile.type });
    await uploadToS3(posterPresign.upload_url, posterFile, (pct) => {
      report({
        stage: "uploading-poster",
        videoProgress: 100,
        posterProgress: pct,
      });
    });
    posterS3Key = posterPresign.s3_key;
  }

  report({ stage: "creating", videoProgress: 100, posterProgress: 100 });

  const task = await createTask({
    ...metadata,
    s3_key: videoPresign.s3_key,
    poster_s3_key: posterS3Key,
  });

  report({ stage: "done", videoProgress: 100, posterProgress: 100 });

  return { taskId: task.id };
}

export function useCancelTaskMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId }: { taskId: string }) =>
      import("#/shared/api/client").then((m) => m.cancelTask(taskId)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}
