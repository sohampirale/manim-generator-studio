"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Clock, ArrowRight, Trash2, Sparkles, History } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { cn } from "@/lib/utils"

interface JobHistoryItem {
  id: string
  prompt: string
  quality: string
  timestamp: string
}

export default function HistoryPage() {
  const [jobHistory, setJobHistory] = useState<JobHistoryItem[]>([])
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const history = JSON.parse(localStorage.getItem("manimJobHistory") || "[]")
    setJobHistory(history)
    setMounted(true)
  }, [])

  const handleClearHistory = () => {
    if (confirm("Are you sure you want to clear your entire history?")) {
      localStorage.setItem("manimJobHistory", "[]")
      setJobHistory([])
    }
  }

  const handleRemoveJob = (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const updatedHistory = jobHistory.filter((job) => job.id !== id)
    localStorage.setItem("manimJobHistory", JSON.stringify(updatedHistory))
    setJobHistory(updatedHistory)
  }

  if (!mounted) return null

  if (jobHistory.length === 0) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
        <div className="h-20 w-20 rounded-3xl bg-primary/5 flex items-center justify-center mb-6">
          <History className="h-10 w-10 text-primary/40" />
        </div>
        <h1 className="text-3xl font-bold mb-3 tracking-tight">No History Yet</h1>
        <p className="text-muted-foreground mb-8 max-w-sm mx-auto">
          You haven't generated any visualizations yet. Start creating to see your history here.
        </p>
        <Button asChild size="lg" className="rounded-full px-8">
          <Link href="/">
            <Sparkles className="h-4 w-4 mr-2" />
            Create Your First Animation
          </Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-12 px-4">
      <div className="flex justify-between items-end border-b border-border/40 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Generation History</h1>
          <p className="text-muted-foreground">Manage your past visualizations</p>
        </div>
        <Button variant="ghost" size="sm" onClick={handleClearHistory} className="text-destructive hover:text-destructive hover:bg-destructive/10">
          Clear All
        </Button>
      </div>

      <div className="space-y-4">
        {jobHistory.map((job) => (
          <Link
            key={job.id}
            href={`/job/${job.id}`}
            className="group block"
          >
            <div className="relative flex items-center justify-between p-6 rounded-2xl border border-border/50 bg-card/50 hover:bg-card hover:border-primary/20 hover:shadow-lg hover:shadow-primary/5 transition-all duration-300">
              <div className="flex-1 min-w-0 pr-6">
                <h3 className="font-semibold text-lg mb-2 truncate group-hover:text-primary transition-colors">
                  {job.prompt}
                </h3>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5" />
                    <span>{formatDistanceToNow(new Date(job.timestamp), { addSuffix: true })}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={cn(
                      "w-2 h-2 rounded-full",
                      job.quality === "l" ? "bg-yellow-500/50" :
                        job.quality === "m" ? "bg-blue-500/50" : "bg-green-500/50"
                    )} />
                    <span className="capitalize">
                      {job.quality === "l" ? "Low" : job.quality === "m" ? "Medium" : "High"} Quality
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => handleRemoveJob(job.id, e)}
                  className="h-9 w-9 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-full"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
                <div className="h-9 w-9 flex items-center justify-center rounded-full bg-primary/10 text-primary">
                  <ArrowRight className="h-4 w-4" />
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
