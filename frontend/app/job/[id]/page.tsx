import { Suspense } from "react"
import JobStatus from "@/components/JobStatus"
import { Skeleton } from "@/components/ui/skeleton"

export default function JobPage({ params }: { params: { id: string } }) {
  return (
    <div className="container max-w-screen-xl mx-auto py-8 px-4">
      <Suspense fallback={<JobStatusSkeleton />}>
        <JobStatus jobId={params.id} />
      </Suspense>
    </div>
  )
}

function JobStatusSkeleton() {
  return (
    <div className="w-full max-w-5xl mx-auto space-y-8 mt-12">
      <div className="flex flex-col md:flex-row justify-between gap-8">
        <div className="space-y-4 w-full md:w-1/2">
          <Skeleton className="h-10 w-3/4" />
          <Skeleton className="h-6 w-1/2" />
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-10 w-24 rounded-full" />
          <Skeleton className="h-10 w-24 rounded-full" />
        </div>
      </div>
      <Skeleton className="aspect-video w-full rounded-2xl" />
    </div>
  )
}
