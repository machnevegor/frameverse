import { useNavigate } from "@tanstack/react-router";
import { Image, Loader2, Upload, X } from "lucide-react";
import { useActionState, useRef, useState, useTransition } from "react";
import { toast } from "sonner";
import * as z from "zod";
import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { Label } from "#/components/ui/label";
import { Progress } from "#/components/ui/progress";
import { Textarea } from "#/components/ui/textarea";
import { type UploadState, uploadMovie } from "./api";

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

const schema = z.object({
  title: z.string().min(1, "Название обязательно"),
  year: z.string().optional(),
  slogan: z.string().optional(),
  genres: z.array(z.string()).optional(),
  short_description: z.string().optional(),
  description: z.string().optional(),
});

type FieldErrors = Partial<
  Record<keyof z.infer<typeof schema> | "root", string>
>;

// ---------------------------------------------------------------------------
// Stage labels
// ---------------------------------------------------------------------------

const STAGE_LABEL: Record<UploadState["stage"], string> = {
  idle: "",
  presign: "Подготовка загрузки...",
  "uploading-video": "Загрузка видео...",
  "uploading-poster": "Загрузка постера...",
  creating: "Создание задачи...",
  done: "Готово",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function UploadMovieForm() {
  const navigate = useNavigate();
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [posterFile, setPosterFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState | null>(null);
  const [genres, setGenres] = useState<string[]>([]);
  const [, startTransition] = useTransition();

  const videoInputRef = useRef<HTMLInputElement>(null);
  const posterInputRef = useRef<HTMLInputElement>(null);

  const isUploading = uploadState !== null && uploadState.stage !== "done";

  const [errors, submitAction, isPending] = useActionState<
    FieldErrors,
    FormData
  >(async (_prev, formData) => {
    const raw = {
      title: formData.get("title") as string,
      year: (formData.get("year") as string) || undefined,
      slogan: (formData.get("slogan") as string) || undefined,
      short_description:
        (formData.get("short_description") as string) || undefined,
      description: (formData.get("description") as string) || undefined,
      genres: genres.length > 0 ? genres : undefined,
    };

    const result = schema.safeParse(raw);
    if (!result.success) {
      const fieldErrors: FieldErrors = {};
      for (const issue of result.error.issues) {
        const key = issue.path[0] as keyof FieldErrors;
        if (!fieldErrors[key]) fieldErrors[key] = issue.message;
      }
      return fieldErrors;
    }

    if (!videoFile) return { root: "Видеофайл обязателен" };

    const { title, year, slogan, short_description, description } = result.data;

    try {
      const { taskId } = await uploadMovie({
        videoFile,
        posterFile,
        metadata: {
          title,
          year: year ? Number(year) : null,
          slogan: slogan?.trim() || null,
          genres: genres.length > 0 ? genres : null,
          description: description?.trim() || null,
          short_description: short_description?.trim() || null,
        },
        onProgress: setUploadState,
      });

      toast.success("Фильм добавлен в обработку");
      startTransition(() => {
        void navigate({
          to: "/dashboard/tasks/$taskId",
          params: { taskId },
        });
      });
      return {};
    } catch {
      toast.error("Ошибка при загрузке фильма");
      setUploadState(null);
      return { root: "Ошибка при загрузке фильма" };
    }
  }, {});

  return (
    <form action={submitAction} className="space-y-6">
      {/* Video */}
      <div className="space-y-2">
        <Label>Видеофайл *</Label>
        <FileDropZone
          accept="video/mp4"
          file={videoFile}
          hint="MP4"
          icon={<Upload className="size-5" />}
          inputRef={videoInputRef}
          label="Перетащите или выберите видеофайл"
          onChange={setVideoFile}
        />
        {errors.root && (
          <p className="text-destructive text-sm">{errors.root}</p>
        )}
      </div>

      {/* Poster — 3:4 vertical slot same width as video */}
      <div className="space-y-2">
        <Label>Постер (необязательно)</Label>
        <FileDropZone
          accept="image/webp"
          file={posterFile}
          hint="WEBP"
          icon={<Image className="size-5" />}
          inputRef={posterInputRef}
          label="Перетащите или выберите постер"
          onChange={setPosterFile}
        />
      </div>

      {/* Upload progress */}
      {uploadState && uploadState.stage !== "idle" && (
        <div className="space-y-3 rounded-lg border p-4">
          <p className="font-medium text-sm">
            {STAGE_LABEL[uploadState.stage]}
          </p>
          <ProgressRow label="Видео" value={uploadState.videoProgress} />
          {posterFile && (
            <ProgressRow label="Постер" value={uploadState.posterProgress} />
          )}
        </div>
      )}

      {/* Fields */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          className="sm:col-span-2"
          error={errors.title}
          label="Название *"
        >
          <Input name="title" placeholder="Официальное название фильма" />
        </Field>

        <Field error={errors.year} label="Год">
          <Input name="year" placeholder="Год выхода" type="number" />
        </Field>

        <Field error={errors.genres} label="Жанры">
          <GenreInput genres={genres} onChange={setGenres} />
        </Field>

        <Field className="sm:col-span-2" error={errors.slogan} label="Слоган">
          <Input
            name="slogan"
            placeholder="Официальный слоган из титров или постера"
          />
        </Field>

        <Field
          className="sm:col-span-2"
          error={errors.short_description}
          label="Краткое описание"
        >
          <Textarea
            className="resize-none"
            name="short_description"
            placeholder="Короткая аннотация — одно-два предложения, как в каталоге"
            rows={2}
          />
        </Field>

        <Field
          className="sm:col-span-2"
          error={errors.description}
          label="Полное описание"
        >
          <Textarea
            className="resize-none"
            name="description"
            placeholder="Развёрнутое описание сюжета из официального источника"
            rows={4}
          />
        </Field>
      </div>

      <SubmitButton disabled={isUploading || isPending} />
    </form>
  );
}

// ---------------------------------------------------------------------------
// Submit button — reads its own pending state via useFormStatus
// ---------------------------------------------------------------------------

function SubmitButton({ disabled }: { disabled: boolean }) {
  return (
    <Button className="w-full" disabled={disabled} type="submit">
      {disabled && <Loader2 className="mr-2 size-4 animate-spin" />}
      {disabled ? "Загружается..." : "Загрузить и обработать"}
    </Button>
  );
}

// ---------------------------------------------------------------------------
// Progress row
// ---------------------------------------------------------------------------

function ProgressRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-muted-foreground text-xs">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <Progress className="h-1.5" value={value} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Generic field wrapper
// ---------------------------------------------------------------------------

function Field({
  label,
  error,
  className,
  children,
}: {
  label: string;
  error?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`space-y-2 ${className ?? ""}`}>
      <Label>{label}</Label>
      {children}
      {error && <p className="text-destructive text-sm">{error}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Genre tag input
// ---------------------------------------------------------------------------

function GenreInput({
  genres,
  onChange,
}: {
  genres: string[];
  onChange: (genres: string[]) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  function commit(raw: string) {
    const trimmed = raw.trim();
    if (trimmed && !genres.includes(trimmed)) {
      onChange([...genres, trimmed]);
    }
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    const v = (e.currentTarget.value ?? "").trim();
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit(v);
    } else if (e.key === "Backspace" && v === "" && genres.length > 0) {
      onChange(genres.slice(0, -1));
    }
  }

  function handleBlur(e: React.FocusEvent<HTMLInputElement>) {
    commit(e.currentTarget.value);
  }

  function remove(genre: string) {
    onChange(genres.filter((g) => g !== genre));
  }

  return (
    // Mimics Input height and border — same ring/border tokens as shadcn Input
    // biome-ignore lint/a11y/noStaticElementInteractions: outer div focuses inner input on click; not interactive itself
    // biome-ignore lint/a11y/useKeyWithClickEvents: outer div focuses inner input on click; not interactive itself
    <div
      className="flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-xs transition-colors focus-within:ring-1 focus-within:ring-ring"
      onClick={() => inputRef.current?.focus()}
    >
      {genres.map((g) => (
        <span
          className="inline-flex items-center gap-1 rounded-sm bg-muted px-1.5 py-0.5 text-muted-foreground text-xs"
          key={g}
        >
          {g}
          <button
            aria-label={`Удалить жанр ${g}`}
            className="rounded-sm opacity-60 hover:opacity-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            onClick={() => remove(g)}
            type="button"
          >
            <X className="size-3" />
          </button>
        </span>
      ))}
      <input
        autoCapitalize="off"
        autoComplete="off"
        autoCorrect="off"
        className="min-w-24 flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
        // On mobile: submit on "Go" / "Done" by capturing Enter via onKeyDown
        enterKeyHint="done"
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        placeholder={genres.length === 0 ? "драма, триллер..." : ""}
        ref={inputRef}
        spellCheck={false}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// File drop zone
// ---------------------------------------------------------------------------

interface FileDropZoneProps {
  accept: string;
  file: File | null;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onChange: (file: File | null) => void;
  icon: React.ReactNode;
  label: string;
  hint: string;
}

function FileDropZone({
  accept,
  file,
  inputRef,
  onChange,
  icon,
  label,
  hint,
}: FileDropZoneProps) {
  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) onChange(f);
  }

  return (
    <label
      className="block w-full cursor-pointer rounded-lg border-2 border-border border-dashed px-6 py-8 text-center transition hover:border-primary/50 hover:bg-accent/30"
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
    >
      <input
        accept={accept}
        className="sr-only"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        ref={inputRef}
        type="file"
      />
      {file ? (
        <div className="space-y-1">
          <p className="break-all font-medium text-sm">{file.name}</p>
          <p className="text-muted-foreground text-xs">
            {(file.size / 1024 / 1024).toFixed(1)} МБ
          </p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          {icon}
          <p className="text-sm">{label}</p>
          <p className="text-xs">{hint}</p>
        </div>
      )}
    </label>
  );
}
