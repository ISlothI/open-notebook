import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Item } from "../api/client";
import { messages } from "../messages";
import { errorText, useToast } from "../ui/toast";

export function useRequestExport(): (item: Item) => void {
  const queries = useQueryClient();
  const toast = useToast();
  const { mutate } = useMutation({
    mutationFn: (item: Item) => api.requestExport(item.id),
    onSuccess: (_export, item) => {
      toast(messages.exports.started(item.title));
      return queries.invalidateQueries({ queryKey: ["exports"] });
    },
    onError: (error) => toast(errorText(error)),
  });
  return mutate;
}
