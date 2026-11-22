import { useQuery } from "@tanstack/react-query";
import { FileQuestion } from "lucide-react";
import { useParams } from "react-router";
import { ApiError, api } from "../api/client";
import { messages } from "../messages";
import { EmptyState } from "../ui/EmptyState";
import { errorText } from "../ui/toast";
import { PageEditor } from "./PageEditor";

export function PageView() {
  const { pageId = "" } = useParams();
  const {
    data: page,
    error,
    refetch,
  } = useQuery({
    queryKey: ["page", pageId],
    queryFn: () => api.page(pageId),
    // The editor owns the text once it is open; refetching must not replace it.
    staleTime: 0,
    gcTime: 0,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  if (page) {
    return <PageEditor key={page.id} page={page} />;
  }
  if (!error) {
    return <div className="centered muted">{messages.loading}</div>;
  }
  if (error instanceof ApiError && error.status === 404) {
    return <EmptyState icon={<FileQuestion size={32} />} title={messages.pages.notFound} />;
  }
  return (
    <div className="centered" role="alert">
      <p>{errorText(error)}</p>
      <button type="button" className="button" onClick={() => refetch()}>
        {messages.retry}
      </button>
    </div>
  );
}
