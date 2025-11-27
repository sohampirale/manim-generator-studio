"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Loader2, RefreshCw, Trash2, Download, ArrowLeft, CheckCircle2, XCircle, Clock, Sparkles, Copy, Check } from "lucide-react"
import { getJobStatus, deleteJob } from "@/lib/api"
import { cn } from "@/lib/utils"

interface JobStatusProps {
  jobId: string
}

interface JobData {
  job_id: string
  status: "pending" | "completed" | "failed"
  message: string
  output_path?: string
}

export default function JobStatus({ jobId }: JobStatusProps) {
  const router = useRouter()
  const [jobData, setJobData] = useState<JobData | null>(null)
  const [isPolling, setIsPolling] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let intervalId: NodeJS.Timeout

    const fetchJobStatus = async () => {
      try {
        const data = await getJobStatus(jobId)
        setJobData(data)

        if (data.status === "completed" || data.status === "failed") {
          setIsPolling(false)
        }

        setIsLoading(false)
      } catch (err) {
        setError("Failed to fetch job status")
        setIsPolling(false)
        setIsLoading(false)
      }
    }

    fetchJobStatus()

    if (isPolling) {
      intervalId = setInterval(fetchJobStatus, 3000)
    }

    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [jobId, isPolling])

  const handleRefresh = async () => {
    setIsLoading(true)
    try {
      const data = await getJobStatus(jobId)
      setJobData(data)
    } catch (err) {
      setError("Failed to refresh job status")
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this job?")) {
      try {
        await deleteJob(jobId)
        const jobHistory = JSON.parse(localStorage.getItem("manimJobHistory") || "[]")
        const updatedHistory = jobHistory.filter((job: any) => job.id !== jobId)
        localStorage.setItem("manimJobHistory", JSON.stringify(updatedHistory))
        router.push("/history")
      } catch (err) {
        setError("Failed to delete job")
      }
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(jobId)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (isLoading && !jobData) {
    return (
      <div className="flex flex-col justify-center items-center min-h-[60vh] space-y-8 animate-in fade-in duration-700">
        <div className="relative">
          <div className="absolute inset-0 bg-primary/20 rounded-full blur-2xl animate-pulse"></div>
          <div className="relative bg-background/50 backdrop-blur-sm p-6 rounded-full border border-primary/10 shadow-xl">
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
          </div>
        </div>
        <div className="text-center space-y-2">
          <h3 className="text-xl font-medium tracking-tight">Loading Job Details</h3>
          <p className="text-muted-foreground animate-pulse">Please wait while we retrieve your animation...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] animate-in zoom-in-95 duration-500">
        <div className="rounded-3xl border border-destructive/20 bg-destructive/5 p-12 text-center max-w-xl mx-auto backdrop-blur-sm shadow-2xl shadow-destructive/5">
          <div className="flex justify-center mb-6">
            <div className="h-20 w-20 rounded-full bg-destructive/10 flex items-center justify-center shadow-inner shadow-destructive/20">
              <XCircle className="h-10 w-10 text-destructive" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-destructive mb-3">Unable to Load Job</h3>
          <p className="text-muted-foreground mb-8 text-lg">{error}</p>
          <Button variant="outline" onClick={() => router.push("/")} className="rounded-full px-8 h-12 border-destructive/20 hover:bg-destructive/10 hover:text-destructive transition-all">
            Return Home
          </Button>
        </div>
      </div>
    )
  }

  if (!jobData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="rounded-3xl border bg-muted/30 p-12 text-center max-w-xl mx-auto backdrop-blur-sm">
          <p className="text-muted-foreground text-xl mb-8 font-light">Job not found</p>
          <Button variant="outline" onClick={() => router.push("/")} className="rounded-full px-8">
            Return Home
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-12 max-w-6xl mx-auto animate-in fade-in duration-700">
      {/* Header Section */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 pb-8 border-b border-border/40">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.push("/")}
              className="rounded-full hover:bg-secondary/80 h-10 w-10 shrink-0"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h2 className="text-4xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/60">
                Generation Status
              </h2>
              <div className="flex items-center gap-3 mt-2 text-muted-foreground">
                <span className="font-mono text-xs opacity-60 bg-muted px-2 py-1 rounded-md border border-border/50">
                  {jobId}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 rounded-md hover:bg-muted"
                  onClick={copyToClipboard}
                >
                  {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
                </Button>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className={cn(
            "px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 border shadow-sm backdrop-blur-sm transition-all duration-300",
            jobData.status === "completed" ? "bg-green-500/10 text-green-600 border-green-500/20 dark:text-green-400 shadow-green-500/5" :
              jobData.status === "failed" ? "bg-destructive/10 text-destructive border-destructive/20 shadow-destructive/5" :
                "bg-blue-500/10 text-blue-500 border-blue-500/20 shadow-blue-500/5"
          )}>
            {jobData.status === "completed" && <CheckCircle2 className="h-4 w-4" />}
            {jobData.status === "failed" && <XCircle className="h-4 w-4" />}
            {jobData.status === "pending" && <Clock className="h-4 w-4 animate-pulse" />}
            <span className="capitalize">{jobData.status}</span>
          </div>

          <div className="h-8 w-px bg-border/50 mx-2 hidden sm:block" />

          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading} className="rounded-full h-10 px-5 border-border/60 hover:bg-secondary/50">
            <RefreshCw className={cn("h-4 w-4 mr-2", isLoading && "animate-spin")} />
            Refresh
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDelete} className="bg-destructive/10 border border-destructive/20 text-destructive hover:bg-destructive/20 hover:text-destructive rounded-full h-10 px-5 transition-colors">
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="min-h-[400px] flex flex-col justify-center">
        {isPolling && (
          <div className="flex flex-col items-center justify-center py-32 bg-gradient-to-b from-muted/20 to-background rounded-[2rem] border border-dashed border-border/60 relative overflow-hidden group">
            <div className="absolute inset-0 bg-grid-white/5 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.6))] -z-10" />
            <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 via-transparent to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />

            <div className="relative mb-10 scale-110">
              <div className="absolute inset-0 bg-primary/30 rounded-full blur-3xl animate-pulse"></div>
              <div className="bg-background/80 backdrop-blur-xl p-6 rounded-full border border-primary/20 shadow-2xl shadow-primary/20 relative z-10 ring-4 ring-primary/5">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
              </div>
            </div>

            <h3 className="text-3xl font-bold mb-4 text-primary animate-pulse">
              Crafting Animation
            </h3>
            <p className="text-muted-foreground max-w-md text-center text-lg leading-relaxed">
              Our AI is generating your visualization. <br />
              <span className="text-sm opacity-60 font-mono mt-2 block">Estimated time: 1-2 minutes</span>
            </p>
          </div>
        )}

        {jobData.status === "completed" && jobData.output_path && (
          <div className="space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-1000">
            <div className="relative aspect-video bg-black rounded-3xl overflow-hidden border border-border/50 shadow-2xl shadow-primary/5 group ring-1 ring-white/10">
              <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent z-10 pointer-events-none" />
              <video
                src={jobData.output_path}
                controls
                autoPlay
                loop
                className="w-full h-full object-contain"
              />
            </div>

            <div className="flex justify-center pb-8">
              <Button asChild size="lg" className="rounded-full px-10 h-14 text-lg shadow-xl shadow-primary/20 hover:shadow-primary/30 transition-all hover:scale-105 hover:-translate-y-1 bg-primary text-primary-foreground border-0">
                <a
                  href={jobData.output_path}
                  download
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Download className="h-5 w-5 mr-3" />
                  Download Video
                </a>
              </Button>
            </div>
          </div>
        )}

        {jobData.status === "failed" && (
          <div className="rounded-[2.5rem] border border-destructive/20 bg-gradient-to-b from-destructive/5 to-background p-16 text-center animate-in zoom-in-95 duration-500 shadow-2xl shadow-destructive/5">
            <div className="flex justify-center mb-8">
              <div className="h-24 w-24 rounded-full bg-destructive/10 flex items-center justify-center shadow-xl shadow-destructive/10 ring-8 ring-destructive/5">
                <XCircle className="h-12 w-12 text-destructive" />
              </div>
            </div>
            <h3 className="text-3xl font-bold text-destructive mb-4 tracking-tight">Generation Failed</h3>
            <p className="text-muted-foreground max-w-lg mx-auto mb-10 text-xl leading-relaxed font-light">
              {jobData.message || "Something went wrong while generating your animation. Please try adjusting your prompt."}
            </p>
            <Button onClick={() => router.push("/")} size="lg" className="rounded-full px-10 h-14 text-lg shadow-lg hover:shadow-xl transition-all hover:scale-105">
              <Sparkles className="h-5 w-5 mr-3" />
              Try New Prompt
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
