import { useState, useEffect } from "react";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export type JobStatus = "pending" | "processing" | "completed" | "error";

export interface JobUpdate {
  status: JobStatus;
  message: string;
}

export function useJobProgress(jobId: string | null, onComplete?: () => void) {
  const [status, setStatus] = useState<JobStatus>("pending");
  const [message, setMessage] = useState<string>("");
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!jobId) {
      setIsOpen(false);
      return;
    }

    setIsOpen(true);
    setStatus("processing");
    setMessage("Connecting to server...");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    // 開発環境と本番環境の両方に対応
    const wsUrl = `${protocol}//${host}/api/ws/jobs/${jobId}`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
      const data: JobUpdate = JSON.parse(event.data);
      setStatus(data.status);
      setMessage(data.message);

      if (data.status === "completed") {
        setTimeout(() => {
          setIsOpen(false);
          if (onComplete) onComplete();
        }, 2000);
      }
    };

    socket.onerror = () => {
      setStatus("error");
      setMessage("WebSocket connection error");
    };

    socket.onclose = () => {
      console.log("WebSocket connection closed");
    };

    return () => {
      socket.close();
    };
  }, [jobId, onComplete]);

  return { status, message, isOpen, setIsOpen };
}

export function JobProgressDialog({ 
  isOpen, 
  status, 
  message 
}: { 
  isOpen: boolean; 
  status: JobStatus; 
  message: string; 
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
      <div className="w-full max-w-sm overflow-hidden rounded-[2rem] bg-card p-8 shadow-2xl border border-border animate-in zoom-in-95 duration-300">
        <div className="flex flex-col items-center text-center space-y-6">
          {status === "processing" && (
            <Loader2 className="h-16 w-16 animate-spin text-primary" />
          )}
          {status === "completed" && (
            <CheckCircle2 className="h-16 w-16 text-green-500 animate-in zoom-in duration-500" />
          )}
          {status === "error" && (
            <AlertCircle className="h-16 w-16 text-destructive animate-in shake duration-500" />
          )}
          
          <div className="space-y-2">
            <h3 className="text-xl font-black tracking-tight">
              {status === "processing" ? "Updating..." : 
               status === "completed" ? "Success!" : "Error"}
            </h3>
            <p className="text-muted-foreground font-medium italic">
              {message}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
