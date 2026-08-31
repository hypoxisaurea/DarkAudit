import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  CheckCircle2,
  LoaderCircle,
  Play,
  Plus,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  useAnalysisStatus,
  useCreateAudit,
  useStartAnalysis,
} from "@/features/audit-create/useAuditWorkflow";
import { cn } from "@/lib/cn";

const auditSchema = z.object({
  name: z.string().trim().min(2, "Audit 이름을 2자 이상 입력해주세요."),
  platform: z.enum(["mobile-web", "desktop-web", "app"]),
});

type AuditForm = z.infer<typeof auditSchema>;
type UploadScreen = { id: string; file: File; previewUrl: string; flowStep: string };

export function AuditCreatePage() {
  const [screens, setScreens] = useState<UploadScreen[]>([]);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number>();
  const [jobId, setJobId] = useState<string>();
  const [createdAuditId, setCreatedAuditId] = useState<string>();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const createAudit = useCreateAudit();
  const startAnalysis = useStartAnalysis();
  const analysis = useAnalysisStatus(jobId);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AuditForm>({
    resolver: zodResolver(auditSchema),
    defaultValues: { name: "", platform: "mobile-web" },
  });

  function addFiles(files: FileList | File[]) {
    const images = Array.from(files)
      .filter((file) => file.type.startsWith("image/"))
      .slice(0, Math.max(0, 15 - screens.length));
    setScreens((current) => [
      ...current,
      ...images.map((file, index) => ({
        id: crypto.randomUUID(),
        file,
        previewUrl: URL.createObjectURL(file),
        flowStep: `화면 ${current.length + index + 1}`,
      })),
    ]);
  }

  function moveScreen(from: number, to: number) {
    if (to < 0 || to >= screens.length) return;
    setScreens((current) => {
      const next = [...current];
      const [item] = next.splice(from, 1);
      if (item) next.splice(to, 0, item);
      return next;
    });
  }

  function removeScreen(id: string) {
    setScreens((current) => {
      const removed = current.find((screen) => screen.id === id);
      if (removed) URL.revokeObjectURL(removed.previewUrl);
      return current.filter((screen) => screen.id !== id);
    });
  }

  async function submit(values: AuditForm) {
    if (!screens.length) return;
    const audit = await createAudit.mutateAsync({
      ...values,
      screens: screens.map((screen) => ({
        id: screen.id,
        flowStep: screen.flowStep,
        fileName: screen.file.name,
      })),
    });
    setCreatedAuditId(audit.id);
    const job = await startAnalysis.mutateAsync(audit.id);
    setJobId(job.jobId);
  }

  const isWorking =
    createAudit.isPending ||
    startAnalysis.isPending ||
    Boolean(jobId && analysis.data?.status !== "completed");

  if (jobId) {
    const progress = analysis.data?.progress ?? 5;
    const completed = analysis.data?.status === "completed";
    return (
      <div className="mx-auto max-w-3xl py-10">
        <Card className="p-8 text-center sm:p-12">
          <span
            className={cn(
              "mx-auto flex size-16 items-center justify-center rounded-full",
              completed ? "bg-success/10 text-success" : "bg-brand-100 text-brand-700",
            )}
          >
            {completed ? (
              <CheckCircle2 size={32} />
            ) : (
              <LoaderCircle className="animate-spin" size={32} />
            )}
          </span>
          <h1 className="mt-6 text-2xl font-bold">
            {completed ? "Audit 분석이 완료되었습니다" : "금융 UX를 분석하고 있습니다"}
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted">
            {completed
              ? "분석 결과와 개선 권고안을 대시보드에서 확인할 수 있습니다."
              : "UI 요소, 문구, 선택 상태와 화면 간 변화를 기준에 따라 검토합니다."}
          </p>
          <div className="mx-auto mt-8 max-w-lg">
            <div className="flex justify-between text-xs">
              <span>분석 진행률</span>
              <strong>{progress}%</strong>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-brand-100">
              <div
                className="h-full rounded-full bg-brand-600 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
          {completed && (
            <Button asChild className="mt-9">
              <Link to={`/app/overview?audit=${createdAuditId}`}>
                결과 확인하기 <ArrowRight size={16} />
              </Link>
            </Button>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl">
      <Link
        className="inline-flex items-center gap-2 text-sm text-muted hover:text-text"
        to="/app/overview"
      >
        <ArrowLeft size={15} /> Overview
      </Link>
      <div className="mt-4">
        <p className="text-xs font-bold uppercase tracking-widest text-brand-600">New Audit</p>
        <h1 className="mt-2 text-3xl font-bold">금융상품 Flow 등록</h1>
        <p className="mt-3 text-sm text-muted">
          실제 이용 순서대로 화면을 등록하면 AI가 전체 흐름을 함께 분석합니다.
        </p>
      </div>

      <form
        className="mt-8 grid gap-6 lg:grid-cols-[0.75fr_1.25fr]"
        onSubmit={handleSubmit(submit)}
      >
        <Card className="h-fit p-6">
          <h2 className="font-bold">Audit 정보</h2>
          <label className="mt-6 block text-sm font-semibold" htmlFor="audit-name">
            Audit 이름
          </label>
          <input
            className="mt-2 w-full rounded-control border border-border px-4 py-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            id="audit-name"
            placeholder="예: 보험 가입 Flow v1"
            {...register("name")}
          />
          {errors.name && <p className="mt-2 text-xs text-danger">{errors.name.message}</p>}
          <label className="mt-5 block text-sm font-semibold" htmlFor="platform">
            플랫폼
          </label>
          <select
            className="mt-2 w-full rounded-control border border-border bg-white px-4 py-3 text-sm outline-none focus:border-brand-500"
            id="platform"
            {...register("platform")}
          >
            <option value="mobile-web">Mobile Web</option>
            <option value="desktop-web">Desktop Web</option>
            <option value="app">Mobile App</option>
          </select>
          <div className="mt-6 rounded-control bg-brand-50 p-4 text-xs leading-6 text-brand-900">
            최대 15개 화면을 등록할 수 있습니다. AI 분석 요청은 백엔드에서 적절한 단위로 나누어
            처리합니다.
          </div>
        </Card>

        <div>
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold">Flow 화면</h2>
                <p className="mt-1 text-xs text-muted">{screens.length} / 15 screens</p>
              </div>
              {screens.length > 0 && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Plus size={15} /> 화면 추가
                </Button>
              )}
            </div>
            <input
              ref={fileInputRef}
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              multiple
              type="file"
              onChange={(event) => event.target.files && addFiles(event.target.files)}
            />
            {screens.length === 0 ? (
              <button
                className={cn(
                  "mt-6 flex min-h-64 w-full flex-col items-center justify-center rounded-card border-2 border-dashed p-8 transition-colors",
                  isDraggingOver
                    ? "border-brand-500 bg-brand-50"
                    : "border-border hover:border-brand-400",
                )}
                type="button"
                onClick={() => fileInputRef.current?.click()}
                onDragEnter={(event) => {
                  event.preventDefault();
                  setIsDraggingOver(true);
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setIsDraggingOver(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  setIsDraggingOver(false);
                  addFiles(event.dataTransfer.files);
                }}
              >
                <span className="flex size-14 items-center justify-center rounded-full bg-brand-100 text-brand-700">
                  <UploadCloud size={27} />
                </span>
                <strong className="mt-5">화면 이미지를 드래그하거나 선택하세요</strong>
                <span className="mt-2 text-xs text-muted">PNG, JPG, WEBP · 화면당 최대 10MB</span>
              </button>
            ) : (
              <div className="mt-6 space-y-3">
                {screens.map((screen, index) => (
                  <div
                    className="grid cursor-grab grid-cols-[64px_1fr_auto] items-center gap-4 rounded-card border border-border bg-white p-3 active:cursor-grabbing"
                    draggable
                    key={screen.id}
                    onDragStart={() => setDraggedIndex(index)}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={() => {
                      if (draggedIndex !== undefined) moveScreen(draggedIndex, index);
                      setDraggedIndex(undefined);
                    }}
                  >
                    <img
                      alt=""
                      className="h-16 w-16 rounded-control border border-border object-cover"
                      src={screen.previewUrl}
                    />
                    <div className="min-w-0">
                      <p className="truncate text-xs text-muted">
                        {index + 1}. {screen.file.name}
                      </p>
                      <input
                        aria-label={`${index + 1}번 화면 단계 이름`}
                        className="mt-2 w-full border-b border-border pb-1 text-sm font-semibold outline-none focus:border-brand-500"
                        value={screen.flowStep}
                        onChange={(event) =>
                          setScreens((current) =>
                            current.map((item) =>
                              item.id === screen.id
                                ? { ...item, flowStep: event.target.value }
                                : item,
                            ),
                          )
                        }
                      />
                    </div>
                    <div className="flex gap-1">
                      <button
                        aria-label="위로 이동"
                        className="p-2 text-muted disabled:opacity-30"
                        disabled={index === 0}
                        type="button"
                        onClick={() => moveScreen(index, index - 1)}
                      >
                        <ArrowUp size={15} />
                      </button>
                      <button
                        aria-label="아래로 이동"
                        className="p-2 text-muted disabled:opacity-30"
                        disabled={index === screens.length - 1}
                        type="button"
                        onClick={() => moveScreen(index, index + 1)}
                      >
                        <ArrowDown size={15} />
                      </button>
                      <button
                        aria-label="화면 삭제"
                        className="p-2 text-danger"
                        type="button"
                        onClick={() => removeScreen(screen.id)}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
          {(createAudit.isError || startAnalysis.isError) && (
            <p className="mt-4 rounded-control bg-danger/10 p-4 text-sm text-danger">
              Audit 요청을 처리하지 못했습니다. 다시 시도해주세요.
            </p>
          )}
          <div className="mt-5 flex justify-end">
            <Button disabled={!screens.length || isWorking} type="submit">
              {isWorking ? <LoaderCircle className="animate-spin" size={16} /> : <Play size={16} />}{" "}
              분석 시작하기
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
