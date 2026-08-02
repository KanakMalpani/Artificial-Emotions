import { QueryClient } from "@tanstack/react-query";

/** Shared TanStack Query client — server state for profiles / runs / etc. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
