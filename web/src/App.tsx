import { useQuery } from "@tanstack/react-query";
import { Route, Routes } from "react-router";
import { ApiError, api } from "./api/client";
import { AuthScreen } from "./auth/AuthScreen";
import { PageView } from "./editor/PageView";
import { ExportsView } from "./exports/ExportsView";
import { LibraryProvider } from "./library/LibraryContext";
import { messages } from "./messages";
import { SectionView, Shell, Welcome } from "./Shell";
import { TrashView } from "./trash/TrashView";
import { errorText } from "./ui/toast";

async function fetchUser() {
  try {
    return await api.me();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export function App() {
  const { data: user, error, refetch } = useQuery({ queryKey: ["me"], queryFn: fetchUser });

  if (user === undefined) {
    return (
      <main className="centered">
        {error ? (
          <>
            <p role="alert">{errorText(error)}</p>
            <button type="button" className="button" onClick={() => refetch()}>
              {messages.retry}
            </button>
          </>
        ) : (
          <p className="muted">{messages.loading}</p>
        )}
      </main>
    );
  }
  if (user === null) {
    return <AuthScreen />;
  }
  return (
    <LibraryProvider>
      <Routes>
        <Route element={<Shell user={user} />}>
          <Route index element={<Welcome />} />
          <Route path="section/:sectionId" element={<SectionView />} />
          <Route path="page/:pageId" element={<PageView />} />
          <Route path="exports" element={<ExportsView />} />
          <Route path="trash" element={<TrashView />} />
          <Route path="*" element={<Welcome />} />
        </Route>
      </Routes>
    </LibraryProvider>
  );
}
