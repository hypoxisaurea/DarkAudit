import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Globe2,
  LoaderCircle,
  Monitor,
  Play,
  Smartphone,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  useAnalysisStatus,
  useCaptureAuditUrl,
  useCreateAudit,
  useStartAnalysis,
  useUploadAuditScreens,
} from "@/features/audit-create/useAuditWorkflow";
import { cn } from "@/lib/cn";

const auditSchema = z.object({
  name: z.string().trim().min(2, "진단 이름을 2자 이상 입력해주세요."),
  platform: z.enum(["mobile-web", "desktop-web", "app"]),
});
type AuditForm = z.infer<typeof auditSchema>;
type UploadScreen = { id: string; file: File; previewUrl: string; flowStep: string };
type DeviceProfile = "desktop" | "mobile";

export function AuditCreatePage() {
  const [source, setSource] = useState<"url" | "upload">("url");
  const [url, setUrl] = useState("");
  const [scanMode, setScanMode] = useState<"quick" | "smart">("quick");
  const [profiles, setProfiles] = useState<DeviceProfile[]>(["desktop", "mobile"]);
  const [goal, setGoal] = useState("");
  const [screens, setScreens] = useState<UploadScreen[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [jobId, setJobId] = useState<string>();
  const [auditId, setAuditId] = useState<string>();
  const inputRef = useRef<HTMLInputElement>(null);
  const createAudit = useCreateAudit();
  const uploadScreens = useUploadAuditScreens();
  const startAnalysis = useStartAnalysis();
  const captureUrl = useCaptureAuditUrl();
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
      .slice(0, 5 - screens.length);
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

  function removeScreen(id: string) {
    setScreens((current) => {
      const removed = current.find((item) => item.id === id);
      if (removed) URL.revokeObjectURL(removed.previewUrl);
      return current.filter((item) => item.id !== id);
    });
  }

  function toggleProfile(profile: DeviceProfile) {
    setProfiles((current) =>
      current.includes(profile)
        ? current.length === 1
          ? current
          : current.filter((item) => item !== profile)
        : [...current, profile],
    );
  }

  async function submit(values: AuditForm) {
    if (source === "url" ? !url.trim() : !screens.length) return;
    const audit = await createAudit.mutateAsync(values);
    setAuditId(audit.id);
    if (source === "url") {
      const job = await captureUrl.mutateAsync({
        auditId: audit.id,
        url: url.trim(),
        mode: scanMode,
        profiles,
        goal: goal.trim() || undefined,
      });
      setJobId(job.jobId);
      return;
    }
    await uploadScreens.mutateAsync({
      auditId: audit.id,
      screens: screens.map(({ id, flowStep, file }) => ({ id, flowStep, file })),
    });
    setJobId((await startAnalysis.mutateAsync(audit.id)).jobId);
  }

  const pending =
    createAudit.isPending ||
    uploadScreens.isPending ||
    startAnalysis.isPending ||
    captureUrl.isPending;
  const requestFailed =
    createAudit.isError || uploadScreens.isError || startAnalysis.isError || captureUrl.isError;

  if (jobId) {
    const completed = analysis.data?.status === "completed";
    const failed = analysis.data?.status === "failed" || analysis.isError;
    const progress = analysis.data?.progress ?? 5;
    return (
      <div className="mx-auto max-w-3xl py-10">
        <Card className="p-8 text-center sm:p-12">
          <span
            className={cn(
              "mx-auto flex size-16 items-center justify-center rounded-full",
              completed
                ? "bg-success/10 text-success"
                : failed
                  ? "bg-danger/10 text-danger"
                  : "bg-brand-100 text-brand-700",
            )}
          >
            {completed ? (
              <CheckCircle2 size={32} />
            ) : failed ? (
              <CircleAlert size={32} />
            ) : (
              <LoaderCircle className="animate-spin" size={32} />
            )}
          </span>
          <h1 className="mt-6 text-2xl font-bold">
            {completed
              ? "진단이 완료되었습니다"
              : failed
                ? "진단을 완료하지 못했습니다"
                : source === "url"
                  ? "사이트를 캡처하고 분석하고 있습니다"
                  : "금융 UX를 분석하고 있습니다"}
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted">
            {completed
              ? "캡처 화면과 AI 진단 결과를 대시보드에서 확인할 수 있습니다."
              : failed
                ? (analysis.data?.error ?? "서버 로그와 AI·Playwright 설정을 확인해주세요.")
                : "선택한 화면 크기로 안전하게 탐색하고 다크패턴 규칙을 검사합니다."}
          </p>
          {!failed && (
            <div className="mx-auto mt-8 max-w-lg">
              <div className="flex justify-between text-xs">
                <span>진행률</span>
                <strong>{progress}%</strong>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-brand-100">
                <div
                  className="h-full rounded-full bg-brand-600 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
          {completed && (
            <Button asChild className="mt-9">
              <Link to={`/app/overview?audit=${auditId}`}>
                결과 확인하기 <ArrowRight size={16} />
              </Link>
            </Button>
          )}
          {failed && (
            <Button className="mt-9" variant="outline" onClick={() => setJobId(undefined)}>
              입력 화면으로 돌아가기
            </Button>
          )}
        </Card>
      </div>
    );
  }

  const canSubmit = source === "url" ? Boolean(url.trim() && profiles.length) : screens.length > 0;
  return (
    <div className="mx-auto max-w-6xl">
      <Link
        className="inline-flex items-center gap-2 text-sm text-muted hover:text-text"
        to="/app/overview"
      >
        <ArrowLeft size={15} /> 대시보드
      </Link>
      <div className="mt-4">
        <p className="text-xs font-bold uppercase tracking-widest text-brand-600">새 진단</p>
        <h1 className="mt-2 text-3xl font-bold">AI UX 진단 시작</h1>
        <p className="mt-3 text-sm text-muted">
          웹사이트 링크만 입력하거나 직접 캡처한 화면을 업로드하세요.
        </p>
      </div>
      <form
        className="mt-8 grid gap-6 lg:grid-cols-[0.75fr_1.25fr]"
        onSubmit={handleSubmit(submit)}
      >
        <Card className="h-fit p-6">
          <h2 className="font-bold">진단 정보</h2>
          <label className="mt-6 block text-sm font-semibold" htmlFor="audit-name">
            진단 이름
          </label>
          <input
            className="mt-2 w-full rounded-control border border-border px-4 py-3 text-sm outline-none focus:border-brand-500"
            id="audit-name"
            placeholder="예: 보험 가입 흐름 v1"
            {...register("name")}
          />
          {errors.name && <p className="mt-2 text-xs text-danger">{errors.name.message}</p>}
          <label className="mt-5 block text-sm font-semibold" htmlFor="platform">
            플랫폼
          </label>
          <select
            className="mt-2 w-full rounded-control border border-border bg-white px-4 py-3 text-sm"
            id="platform"
            {...register("platform")}
          >
            <option value="mobile-web">모바일 웹</option>
            <option value="desktop-web">데스크톱 웹</option>
            <option value="app">모바일 앱</option>
          </select>
          <div className="mt-6 rounded-control bg-brand-50 p-4 text-xs leading-6 text-brand-900">
            URL 진단은 공개 HTTP(S) 사이트만 접근하며 결제·가입·제출 같은 위험 동작은 수행하지
            않습니다.
          </div>
        </Card>
        <div>
          <Card className="p-6">
            <div
              className="grid grid-cols-2 gap-2 rounded-control bg-black/[0.035] p-1"
              role="tablist"
              aria-label="진단 입력 방식"
            >
              <button
                className={cn(
                  "flex items-center justify-center gap-2 rounded-control px-3 py-3 text-sm font-semibold",
                  source === "url" && "bg-white text-brand-700 shadow-sm",
                )}
                role="tab"
                aria-selected={source === "url"}
                type="button"
                onClick={() => setSource("url")}
              >
                <Globe2 size={17} /> 웹사이트 URL
              </button>
              <button
                className={cn(
                  "flex items-center justify-center gap-2 rounded-control px-3 py-3 text-sm font-semibold",
                  source === "upload" && "bg-white text-brand-700 shadow-sm",
                )}
                role="tab"
                aria-selected={source === "upload"}
                type="button"
                onClick={() => setSource("upload")}
              >
                <UploadCloud size={17} /> 스크린샷 업로드
              </button>
            </div>
            {source === "url" ? (
              <UrlFields
                url={url}
                setUrl={setUrl}
                profiles={profiles}
                toggleProfile={toggleProfile}
                scanMode={scanMode}
                setScanMode={setScanMode}
                goal={goal}
                setGoal={setGoal}
              />
            ) : (
              <UploadFields
                screens={screens}
                setScreens={setScreens}
                inputRef={inputRef}
                dragOver={dragOver}
                setDragOver={setDragOver}
                addFiles={addFiles}
                removeScreen={removeScreen}
              />
            )}
          </Card>
          {requestFailed && (
            <p className="mt-4 rounded-control bg-danger/10 p-4 text-sm text-danger">
              진단 요청을 처리하지 못했습니다. 입력값과 서버 설정을 확인해주세요.
            </p>
          )}
          <div className="mt-5 flex justify-end">
            <Button disabled={!canSubmit || pending} type="submit">
              {pending ? <LoaderCircle className="animate-spin" size={16} /> : <Play size={16} />}{" "}
              분석 시작하기
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}

function UrlFields({
  url,
  setUrl,
  profiles,
  toggleProfile,
  scanMode,
  setScanMode,
  goal,
  setGoal,
}: {
  url: string;
  setUrl: (value: string) => void;
  profiles: DeviceProfile[];
  toggleProfile: (profile: DeviceProfile) => void;
  scanMode: "quick" | "smart";
  setScanMode: (mode: "quick" | "smart") => void;
  goal: string;
  setGoal: (value: string) => void;
}) {
  return (
    <div className="mt-6">
      <label className="block text-sm font-semibold" htmlFor="target-url">
        검사할 웹사이트 주소
      </label>
      <input
        className="mt-2 w-full rounded-control border border-border px-4 py-3 text-sm outline-none focus:border-brand-500"
        id="target-url"
        type="url"
        required
        placeholder="https://example.com/product"
        value={url}
        onChange={(event) => setUrl(event.target.value)}
      />
      <p className="mt-5 text-sm font-semibold">캡처 화면</p>
      <div className="mt-2 grid gap-3 sm:grid-cols-2">
        {(["desktop", "mobile"] as const).map((profile) => {
          const selected = profiles.includes(profile);
          const Icon = profile === "desktop" ? Monitor : Smartphone;
          return (
            <button
              key={profile}
              className={cn(
                "flex items-center gap-3 rounded-control border p-4 text-left",
                selected ? "border-brand-500 bg-brand-50" : "border-border",
              )}
              type="button"
              aria-pressed={selected}
              onClick={() => toggleProfile(profile)}
            >
              <Icon size={20} />
              <span>
                <strong className="block text-sm">
                  {profile === "desktop" ? "데스크톱" : "모바일"}
                </strong>
                <small className="text-muted">
                  {profile === "desktop" ? "1440 × 900" : "390 × 844"}
                </small>
              </span>
            </button>
          );
        })}
      </div>
      <p className="mt-5 text-sm font-semibold">탐색 방식</p>
      <div className="mt-2 grid gap-3 sm:grid-cols-2">
        <ModeButton
          active={scanMode === "quick"}
          title="빠른 캡처"
          description="Playwright로 첫 화면과 전체 페이지 캡처"
          onClick={() => setScanMode("quick")}
        />
        <ModeButton
          active={scanMode === "smart"}
          title="스마트 탐색"
          description="Computer Use로 안전한 흐름 추가 탐색"
          smart
          onClick={() => setScanMode("smart")}
        />
      </div>
      {scanMode === "smart" && (
        <div className="mt-4">
          <label className="block text-sm font-semibold" htmlFor="audit-goal">
            탐색 목표 <span className="font-normal text-muted">(선택)</span>
          </label>
          <textarea
            className="mt-2 min-h-24 w-full rounded-control border border-border px-4 py-3 text-sm outline-none focus:border-brand-500"
            id="audit-goal"
            placeholder="예: 옵션 선택부터 최종 가격 확인 직전까지"
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
          />
        </div>
      )}
    </div>
  );
}

function ModeButton({
  active,
  title,
  description,
  smart,
  onClick,
}: {
  active: boolean;
  title: string;
  description: string;
  smart?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={cn(
        "rounded-control border p-4 text-left",
        active ? "border-brand-500 bg-brand-50" : "border-border",
      )}
      type="button"
      onClick={onClick}
    >
      <strong className="flex items-center gap-2 text-sm">
        {smart && <Sparkles size={15} />}
        {title}
      </strong>
      <span className="mt-1 block text-xs text-muted">{description}</span>
    </button>
  );
}

function UploadFields({
  screens,
  setScreens,
  inputRef,
  dragOver,
  setDragOver,
  addFiles,
  removeScreen,
}: {
  screens: UploadScreen[];
  setScreens: React.Dispatch<React.SetStateAction<UploadScreen[]>>;
  inputRef: React.RefObject<HTMLInputElement | null>;
  dragOver: boolean;
  setDragOver: (value: boolean) => void;
  addFiles: (files: FileList | File[]) => void;
  removeScreen: (id: string) => void;
}) {
  return (
    <div className="mt-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-bold">검사할 화면</h2>
          <p className="mt-1 text-xs text-muted">{screens.length} / 5개 화면</p>
        </div>
        {screens.length > 0 && (
          <Button type="button" variant="outline" onClick={() => inputRef.current?.click()}>
            화면 추가
          </Button>
        )}
      </div>
      <input
        ref={inputRef}
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        multiple
        type="file"
        onChange={(event) => event.target.files && addFiles(event.target.files)}
      />
      {screens.length === 0 ? (
        <button
          className={cn(
            "mt-6 flex min-h-64 w-full flex-col items-center justify-center rounded-card border-2 border-dashed p-8",
            dragOver ? "border-brand-500 bg-brand-50" : "border-border",
          )}
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragEnter={(event) => {
            event.preventDefault();
            setDragOver(true);
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragOver(false);
            addFiles(event.dataTransfer.files);
          }}
        >
          <UploadCloud className="text-brand-700" size={30} />
          <strong className="mt-4">화면 이미지를 드래그하거나 선택하세요</strong>
          <span className="mt-2 text-xs text-muted">PNG, JPG, WEBP · 화면당 최대 10MB</span>
        </button>
      ) : (
        <div className="mt-5 space-y-3">
          {screens.map((item, index) => (
            <div
              className="grid grid-cols-[64px_1fr_auto] items-center gap-4 rounded-card border border-border p-3"
              key={item.id}
            >
              <img alt="" className="size-16 rounded-control object-cover" src={item.previewUrl} />
              <div>
                <p className="truncate text-xs text-muted">
                  {index + 1}. {item.file.name}
                </p>
                <input
                  aria-label={`${index + 1}번 화면 단계 이름`}
                  className="mt-2 w-full border-b border-border pb-1 text-sm font-semibold outline-none"
                  value={item.flowStep}
                  onChange={(event) =>
                    setScreens((current) =>
                      current.map((screen) =>
                        screen.id === item.id
                          ? { ...screen, flowStep: event.target.value }
                          : screen,
                      ),
                    )
                  }
                />
              </div>
              <button
                aria-label="화면 삭제"
                className="p-2 text-danger"
                type="button"
                onClick={() => removeScreen(item.id)}
              >
                <X size={17} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
