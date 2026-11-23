"use client";

import { useEffect, useState } from "react";
import { Download, ExternalLink } from "lucide-react";
import { Button, ErrorBox, Modal, Spinner } from "./ui";
import { fileObjectUrl } from "@/lib/api";

/** Previews a private document by fetching it with the bearer token (no public URLs). */
export function DocumentViewer({ docId, title, onClose }: { docId: string | null; title?: string | null; onClose: () => void }) {
  const [url, setUrl] = useState<string | null>(null);
  const [type, setType] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!docId) return;
    let revoked = false;
    let objectUrl: string | null = null;
    setUrl(null); setError(null);
    fileObjectUrl(docId)
      .then(async (u) => {
        objectUrl = u;
        const blob = await fetch(u).then((r) => r.blob());
        if (!revoked) { setType(blob.type); setUrl(u); }
      })
      .catch((e) => !revoked && setError((e as Error).message));
    return () => { revoked = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [docId]);

  async function download() {
    if (!docId) return;
    const u = await fileObjectUrl(docId, true);
    const a = document.createElement("a");
    a.href = u;
    a.download = (title || "document").replace(/[^\w.-]+/g, "_") + (type.includes("pdf") ? ".pdf" : type.includes("png") ? ".png" : ".jpg");
    a.click();
    setTimeout(() => URL.revokeObjectURL(u), 2000);
  }

  return (
    <Modal open={!!docId} onClose={onClose} title={title || "Document"} wide
      footer={url ? <>
        <Button variant="secondary" size="sm" onClick={() => window.open(url, "_blank", "noopener")}><ExternalLink className="h-4 w-4" /> Open</Button>
        <Button size="sm" onClick={download}><Download className="h-4 w-4" /> Download</Button>
      </> : undefined}>
      {error && <ErrorBox message={error} />}
      {!error && !url && <Spinner label="Loading private document…" />}
      {url && (type.includes("pdf")
        ? <iframe src={url} title={title || "Document"} className="h-[65vh] w-full rounded-xl border border-slate-200" />
        // eslint-disable-next-line @next/next/no-img-element
        : <img src={url} alt={title || "Document"} className="mx-auto max-h-[65vh] rounded-xl border border-slate-200" />)}
      <p className="mt-3 text-xs text-slate-500">Served through an authenticated API call and checked against ownership/consent. Synthetic demo document.</p>
    </Modal>
  );
}
