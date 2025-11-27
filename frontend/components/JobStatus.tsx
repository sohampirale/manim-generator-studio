"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, RefreshCw, Trash2, Download, ArrowLeft, CheckCircle2, XCircle, Clock } from "lucide-react"
import { getJobStatus, getJobCode, deleteJob } from "@/lib/api"
import CodeViewer from "@/components/CodeViewer"
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
  const [code, setCode] = useState<string>("")
  const [isPolling, setIsPolling] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let intervalId: NodeJS.Timeout

    const fetchJobStatus = async () => {
      try {
        const data = await getJobStatus(jobId)
        setJobData(data)

        if (data.status === "completed" || data.status === "failed") {
          setIsPolling(false)

          if (data.status === "completed") {
            try {
              const codeData = await getJobCode(jobId)
              setCode(codeData?.code)
            } catch (err) {
              console.error("Error fetching code:", err)
            }
          }
        }

        setIsLoading(false)
      } catch (err) {
        setError("Failed to fetch job status")
        setIsPolling(false)
        setIsLoading(false)
      }
    }


    fetchJobStatus()

    // Set up polling if needed
    if (isPolling) {
      intervalId = setInterval(fetchJobStatus, 6000)
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

      if (data.status === "completed") {
        try {
          const codeData = await getJobCode(jobId)
          setCode(codeData)
        } catch (err) {
          console.error("Error fetching code:", err)
        }
      }
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

        // Remove from localStorage
        const jobHistory = JSON.parse(localStorage.getItem("manimJobHistory") || "[]")
        const updatedHistory = jobHistory.filter((job: any) => job.id !== jobId)
        localStorage.setItem("manimJobHistory", JSON.stringify(updatedHistory))

        router.push("/history")
      } catch (err) {
        setError("Failed to delete job")
      }
    }
  }

  if (isLoading && !jobData) {
    return (
      <div className="flex flex-col justify-center items-center py-24 space-y-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-muted-foreground animate-pulse">Loading job details...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
        <div className="flex justify-center mb-4">
          <XCircle className="h-10 w-10 text-destructive" />
        </div>
        <h3 className="text-lg font-semibold text-destructive mb-2">Error</h3>
        <p className="text-muted-foreground">{error}</p>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/")}>
          Return Home
        </Button>
      </div>
    )
  }

  if (!jobData) {
    return (
      <div className="rounded-xl border bg-muted/30 p-8 text-center">
        <p className="text-muted-foreground">Job not found</p>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/")}>
          Return Home
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-border/40">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-3xl font-bold tracking-tight">Generation Status</h2>
            <div className={cn(
              "px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 border",
              jobData.status === "completed" ? "bg-primary/10 text-primary border-primary/20" :
                jobData.status === "failed" ? "bg-destructive/10 text-destructive border-destructive/20" :
                  "bg-blue-500/10 text-blue-500 border-blue-500/20"
            )}>
              {jobData.status === "completed" && <CheckCircle2 className="h-3.5 w-3.5" />}
              {jobData.status === "failed" && <XCircle className="h-3.5 w-3.5" />}
              {jobData.status === "pending" && <Clock className="h-3.5 w-3.5 animate-pulse" />}
              <span className="capitalize">{jobData.status}</span>
            </div>
          </div>
          <p className="text-muted-foreground font-mono text-sm">
            ID: {jobId}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" size="sm" onClick={() => router.push("/")} className="rounded-full">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading} className="rounded-full">
            <RefreshCw className={cn("h-4 w-4 mr-2", isLoading && "animate-spin")} />
            Refresh
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDelete} className="text-destructive hover:text-destructive hover:bg-destructive/10 rounded-full">
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {isPolling && (
        <div className="flex flex-col items-center justify-center py-16 bg-muted/20 rounded-3xl border border-dashed border-border/60">
          <div className="relative mb-6">
            <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse"></div>
            <Loader2 className="h-12 w-12 animate-spin text-primary relative z-10" />
          </div>
          <h3 className="text-xl font-semibold mb-2">Generating Animation</h3>
          <p className="text-muted-foreground max-w-md text-center">
            Our AI is crafting your visualization. This usually takes 1-2 minutes depending on complexity.
          </p>
        </div>
      )}

      {jobData.status === "completed" && jobData.output_path && (
        <Tabs defaultValue="video" className="w-full">
          <div className="flex justify-center mb-8">
            <TabsList className="grid w-full max-w-md grid-cols-2 p-1 bg-muted/50 rounded-full">
              <TabsTrigger value="video" className="rounded-full data-[state=active]:bg-background data-[state=active]:shadow-sm">Video Preview</TabsTrigger>
              <TabsTrigger value="code" className="rounded-full data-[state=active]:bg-background data-[state=active]:shadow-sm">Generated Code</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="video" className="space-y-6 animate-fade-in">
            <div className="relative aspect-video bg-black/5 rounded-2xl overflow-hidden border border-border/50 shadow-2xl shadow-primary/5">
              <video
                src={jobData.output_path}
                controls
                className="w-full h-full"
              />
            </div>

            <div className="flex justify-center">
              <Button asChild size="lg" className="rounded-full px-8 shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all">
                <a
                  href={jobData.output_path}
                  download
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download Video
                </a>
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="code" className="animate-fade-in">
            <CodeViewer code={code} />
          </TabsContent>
        </Tabs>
      )}

      {jobData.status === "failed" && (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <XCircle className="h-6 w-6 text-destructive" />
            </div>
          </div>
          <h3 className="text-xl font-semibold text-destructive mb-2">Generation Failed</h3>
          <p className="text-muted-foreground max-w-lg mx-auto mb-6">
            {jobData.message || "Something went wrong while generating your animation. Please try adjusting your prompt."}
          </p>
          <Button onClick={() => router.push("/")} className="rounded-full">
            Try Again
          </Button>
        </div>
      )}
    </div>
  )
}
