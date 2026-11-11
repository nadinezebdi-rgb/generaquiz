import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { adoptAccountStreak, dropPendingMini, listPendingMini, loadStreak } from "@/lib/visitorProgress";

// Dès qu'un compte est connecté : rattache le mini-quiz joué en visiteur et fusionne la série du conseil.
export const VisitorProgressSync = () => {
  const { user } = useAuth();
  const doneFor = useRef(null);

  useEffect(() => {
    const uid = user?.id || user?.email;
    if (!user || doneFor.current === uid) return;
    doneFor.current = uid;

    listPendingMini().forEach((pending) => {
      api.post("/mini-quiz/claim", { category_id: pending.category_id, answers: pending.answers })
        .then(({ data }) => {
          dropPendingMini(pending.category_id);
          if (!data.already_claimed) toast.success(`Votre score du mini-quiz (${data.score}/${data.total}) a été ajouté à votre historique`);
        })
        .catch((e) => { if (e.response?.status === 400) dropPendingMini(pending.category_id); });
    });

    const st = loadStreak();
    const sync = st.last_date
      ? api.post("/tips/streak/merge", { count: st.count, best: st.best || 0, last_date: st.last_date, last_result: !!st.last_result })
      : api.get("/tips/streak/me");
    sync.then(({ data }) => adoptAccountStreak(data)).catch(() => {});
  }, [user]);

  return null;
};
