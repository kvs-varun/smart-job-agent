"use client";

import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as Select from "@radix-ui/react-select";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import {
  Calendar,
  Check,
  ChevronDown,
  ChevronUp,
  MoreHorizontal,
  Plus,
  Target,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

type Status = "Applied" | "Screening" | "Interview" | "Offer" | "Rejected";
type View = "table" | "pipeline";

type Application = {
  id: string;
  company: string;
  role: string;
  dateApplied: string;
  matchScore: number;
  status: Status;
  jobUrl?: string;
  notes?: string;
};

const STATUS_COLORS: Record<Status, { bg: string; text: string; border: string }> = {
  Applied: { bg: "bg-[#6366F1]/15", text: "text-[#A5B4FC]", border: "border-[#6366F1]/30" },
  Screening: { bg: "bg-[#14B8A6]/15", text: "text-[#5EEAD4]", border: "border-[#14B8A6]/30" },
  Interview: { bg: "bg-[#F59E0B]/15", text: "text-[#FCD34D]", border: "border-[#F59E0B]/30" },
  Offer: { bg: "bg-[#10B981]/15", text: "text-[#6EE7B7]", border: "border-[#10B981]/30" },
  Rejected: { bg: "bg-[#EF4444]/15", text: "text-[#FCA5A5]", border: "border-[#EF4444]/30" },
};

function statusBadge(status: Status) {
  const c = STATUS_COLORS[status];
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium", c.bg, c.text, c.border)}>
      {status}
    </span>
  );
}

function scoreBadge(score: number) {
  if (score >= 75) return <span className="inline-flex rounded-full bg-[#10B981]/15 border border-[#10B981]/25 px-2.5 py-0.5 text-xs font-medium text-[#6EE7B7]">{score}%</span>;
  if (score >= 50) return <span className="inline-flex rounded-full bg-[#F59E0B]/15 border border-[#F59E0B]/25 px-2.5 py-0.5 text-xs font-medium text-[#FCD34D]">{score}%</span>;
  return <span className="inline-flex rounded-full bg-[#EF4444]/15 border border-[#EF4444]/25 px-2.5 py-0.5 text-xs font-medium text-[#FCA5A5]">{score}%</span>;
}

export default function TrackerPage() {
  const [view, setView] = React.useState<View>("table");
  const [open, setOpen] = React.useState(false);
  const [apps, setApps] = React.useState<Application[]>(() => []);

  const stats = React.useMemo(() => {
    const total = apps.length;
    const interviews = apps.filter((a) => a.status === "Interview").length;
    const offers = apps.filter((a) => a.status === "Offer").length;
    const avg = total ? Math.round(apps.reduce((acc, a) => acc + a.matchScore, 0) / total) : 0;
    return { total, interviews, offers, avg };
  }, [apps]);

  function updateStatus(id: string, status: Status) {
    setApps((prev) => prev.map((a) => (a.id === id ? { ...a, status } : a)));
  }

  function removeApp(id: string) {
    setApps((prev) => prev.filter((a) => a.id !== id));
    toast("Application removed");
  }

  return (
    <div className="pb-10">
      <div className="flex items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="font-heading font-extrabold text-3xl md:text-[32px] gradient-text">Application Tracker</h1>
          <div className="mt-2 text-sm text-[#94A3B8]">Track your pipeline and keep your job search organized.</div>
        </div>
        <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setOpen(true)}>
          Add Application
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Applications" value={stats.total} />
        <StatCard label="Interviews Scheduled" value={stats.interviews} accent="teal" />
        <StatCard label="Offers" value={stats.offers} accent="success" />
        <StatCard label="Avg Match Score" value={stats.avg} suffix="%" />
      </div>

      <div className="flex items-center gap-2 mb-6">
        <Button variant={view === "table" ? "subtle" : "ghost"} size="sm" onClick={() => setView("table")}>
          Table View
        </Button>
        <Button variant={view === "pipeline" ? "subtle" : "ghost"} size="sm" onClick={() => setView("pipeline")}>
          Pipeline View
        </Button>
      </div>

      {apps.length === 0 ? (
        <div className="rounded-2xl border border-[#334155] bg-[#1E293B] p-10 text-center">
          <div className="mx-auto w-fit text-[#334155]">
            <Target className="w-14 h-14" />
          </div>
          <div className="mt-4 font-heading font-semibold text-white">Tracker is empty</div>
          <div className="mt-2 text-sm text-[#94A3B8]">Add your first application to get started.</div>
          <div className="mt-6 flex justify-center">
            <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setOpen(true)}>
              Add Application
            </Button>
          </div>
        </div>
      ) : view === "table" ? (
        <div className="overflow-x-auto rounded-2xl border border-[#334155] bg-[#1E293B]">
          <table className="min-w-[920px] w-full">
            <thead>
              <tr className="border-b border-[#334155] text-left text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">
                <th className="px-6 py-4">Company</th>
                <th className="px-6 py-4">Role</th>
                <th className="px-6 py-4">Date Applied</th>
                <th className="px-6 py-4">Match</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#334155]/60">
              {apps.map((a, idx) => (
                <motion.tr
                  key={a.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, delay: idx * 0.05 }}
                  className="hover:bg-[#243044]/40"
                >
                  <td className="px-6 py-4 text-sm font-medium text-white">{a.company}</td>
                  <td className="px-6 py-4 text-sm text-[#94A3B8]">{a.role}</td>
                  <td className="px-6 py-4 text-sm text-[#94A3B8]">
                    <span className="inline-flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-[#64748B]" />
                      {a.dateApplied}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">{scoreBadge(a.matchScore)}</td>
                  <td className="px-6 py-4 text-sm">
                    <StatusSelect value={a.status} onValueChange={(v) => updateStatus(a.id, v)} />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      className="inline-flex items-center justify-center rounded-lg border border-[#334155] bg-[#243044] px-2.5 py-2 text-[#94A3B8] hover:text-white hover:border-[#6366F1] transition-all"
                      onClick={() => toast("Actions menu — coming soon")}
                      aria-label="Actions"
                    >
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                    <button
                      className="ml-2 inline-flex items-center justify-center rounded-lg border border-[#EF4444]/30 bg-[#EF4444]/10 px-2.5 py-2 text-[#FCA5A5] hover:text-white transition-all"
                      onClick={() => removeApp(a.id)}
                      aria-label="Delete"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <PipelineView apps={apps} />
      )}

      <AddApplicationDialog
        open={open}
        onOpenChange={setOpen}
        onAdd={(app) => {
          setApps((prev) => [app, ...prev]);
          toast("Application added");
        }}
      />
    </div>
  );
}

function StatCard({
  label,
  value,
  suffix,
  accent,
}: {
  label: string;
  value: number;
  suffix?: string;
  accent?: "teal" | "success";
}) {
  const color = accent === "teal" ? "text-[#5EEAD4]" : accent === "success" ? "text-[#6EE7B7]" : "gradient-text";
  return (
    <div className="bg-[#1E293B] border border-[#334155] rounded-xl p-5">
      <div className="text-sm text-[#94A3B8]">{label}</div>
      <div className={cn("mt-2 font-heading font-extrabold text-3xl", color)}>
        <CountUp end={value} duration={1.2} />
        {suffix}
      </div>
    </div>
  );
}

function StatusSelect({ value, onValueChange }: { value: Status; onValueChange: (value: Status) => void }) {
  return (
    <Select.Root value={value} onValueChange={(v) => onValueChange(v as Status)}>
      <Select.Trigger className="inline-flex items-center justify-between gap-2 rounded-lg border border-[#334155] bg-[#243044] px-3 py-2 text-xs font-medium text-white hover:border-[#6366F1] transition-all">
        <Select.Value>{value}</Select.Value>
        <Select.Icon>
          <ChevronDown className="w-4 h-4 text-[#94A3B8]" />
        </Select.Icon>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content className="z-[60] overflow-hidden rounded-xl border border-[#334155] bg-[#1E293B] shadow-2xl">
          <Select.ScrollUpButton className="flex items-center justify-center py-2 text-[#94A3B8]">
            <ChevronUp className="w-4 h-4" />
          </Select.ScrollUpButton>
          <Select.Viewport className="p-1">
            {(["Applied", "Screening", "Interview", "Offer", "Rejected"] as Status[]).map((s) => (
              <Select.Item
                key={s}
                value={s}
                className="relative flex cursor-pointer select-none items-center rounded-lg px-3 py-2 text-sm text-white outline-none data-[highlighted]:bg-[#243044]"
              >
                <Select.ItemText>{s}</Select.ItemText>
                <Select.ItemIndicator className="absolute right-2 inline-flex items-center">
                  <Check className="w-4 h-4 text-[#10B981]" />
                </Select.ItemIndicator>
              </Select.Item>
            ))}
          </Select.Viewport>
          <Select.ScrollDownButton className="flex items-center justify-center py-2 text-[#94A3B8]">
            <ChevronDown className="w-4 h-4" />
          </Select.ScrollDownButton>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}

function PipelineView({ apps }: { apps: Application[] }) {
  const columns: Status[] = ["Applied", "Screening", "Interview", "Offer", "Rejected"];
  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
      {columns.map((col) => {
        const items = apps.filter((a) => a.status === col);
        return (
          <div key={col} className="rounded-2xl border border-[#334155] bg-[#1E293B] overflow-hidden">
            <div className="px-4 py-3 border-b border-[#334155] flex items-center justify-between">
              <div className="text-sm font-semibold text-white">{col}</div>
              <div className="text-xs text-[#94A3B8]">{items.length}</div>
            </div>
            <div className="p-3">
              {items.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#334155] p-5 text-center text-sm text-[#64748B]">
                  Drop here
                </div>
              ) : (
                <div className="space-y-3">
                  {items.map((a) => (
                    <div key={a.id} className="rounded-xl border border-[#334155] bg-[#243044]/40 p-4">
                      <div className="text-sm font-semibold text-white">{a.company}</div>
                      <div className="mt-1 text-xs text-[#94A3B8]">{a.role}</div>
                      <div className="mt-3 flex items-center justify-between">
                        <span className="text-xs text-[#64748B]">{a.dateApplied}</span>
                        {scoreBadge(a.matchScore)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AddApplicationDialog({
  open,
  onOpenChange,
  onAdd,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (app: Application) => void;
}) {
  const [company, setCompany] = React.useState("");
  const [role, setRole] = React.useState("");
  const [jobUrl, setJobUrl] = React.useState("");
  const [dateApplied, setDateApplied] = React.useState(() => new Date().toISOString().slice(0, 10));
  const [matchScore, setMatchScore] = React.useState(70);
  const [status, setStatus] = React.useState<Status>("Applied");
  const [notes, setNotes] = React.useState("");

  React.useEffect(() => {
    if (!open) {
      setCompany("");
      setRole("");
      setJobUrl("");
      setNotes("");
      setMatchScore(70);
      setStatus("Applied");
      setDateApplied(new Date().toISOString().slice(0, 10));
    }
  }, [open]);

  function onSubmit() {
    if (!company.trim() || !role.trim()) {
      toast("Company and role are required.");
      return;
    }
    const app: Application = {
      id: crypto.randomUUID(),
      company: company.trim(),
      role: role.trim(),
      jobUrl: jobUrl.trim() || undefined,
      notes: notes.trim() || undefined,
      dateApplied,
      matchScore: Math.max(0, Math.min(100, Math.round(matchScore))),
      status,
    };
    onAdd(app);
    onOpenChange(false);
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-[calc(100vw-32px)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[#334155] bg-[#1E293B] p-6 shadow-2xl">
          <div className="flex items-center justify-between">
            <Dialog.Title className="font-heading font-bold text-xl text-white">Add Application</Dialog.Title>
            <Dialog.Close asChild>
              <button className="text-[#94A3B8] hover:text-white" aria-label="Close">
                <X className="w-5 h-5" />
              </button>
            </Dialog.Close>
          </div>

          <div className="mt-6 grid gap-4">
            <div>
              <div className="text-sm font-medium text-[#94A3B8]">Company Name</div>
              <input value={company} onChange={(e) => setCompany(e.target.value)} className={inputCls} placeholder="Acme" />
            </div>
            <div>
              <div className="text-sm font-medium text-[#94A3B8]">Role / Job Title</div>
              <input value={role} onChange={(e) => setRole(e.target.value)} className={inputCls} placeholder="Backend Engineer" />
            </div>
            <div>
              <div className="text-sm font-medium text-[#94A3B8]">Job URL (optional)</div>
              <input value={jobUrl} onChange={(e) => setJobUrl(e.target.value)} className={inputCls} placeholder="https://..." />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-sm font-medium text-[#94A3B8]">Date Applied</div>
                <input type="date" value={dateApplied} onChange={(e) => setDateApplied(e.target.value)} className={inputCls} />
              </div>
              <div>
                <div className="text-sm font-medium text-[#94A3B8]">Match Score</div>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={matchScore}
                  onChange={(e) => setMatchScore(Number(e.target.value))}
                  className={inputCls}
                />
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-[#94A3B8]">Status</div>
              <div className="mt-2">{statusBadge(status)}</div>
              <div className="mt-2">
                <StatusSelect value={status} onValueChange={setStatus} />
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-[#94A3B8]">Notes (optional)</div>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} className={textareaCls} rows={3} />
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={onSubmit}>
              Add Application
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const inputCls =
  "mt-2 w-full rounded-lg border border-[#334155] bg-[#243044] px-4 py-2.5 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] focus:ring-2 focus:ring-[#6366F1]/20 transition-all outline-none";

const textareaCls =
  "mt-2 w-full rounded-lg border border-[#334155] bg-[#243044] px-4 py-2.5 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] focus:ring-2 focus:ring-[#6366F1]/20 transition-all outline-none resize-none";
