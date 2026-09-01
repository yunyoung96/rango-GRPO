(* ★★★ 적용가능성 필터 — Coq 커널을 직접 부른다.
 *
 * ## 설계는 Coq 자신의 것을 따른다
 *
 * `tactics/hints.ml:252` 가 `auto`/`eauto` 의 hint DB 를 이렇게 적어 두었다 —
 *   "un discrimination net borné (Btermdn.t) constitué de tous les patterns"
 * 즉 **결론 패턴을 판별트리에 넣고 goal 로 조회**한다. 여기서도 같은 구조다.
 *
 * 색인 셋을 만든다 (파일당 한 번):
 *   dn_apply  후보 타입의 **모든 화살표 접미사 결론** → (후보, 깊이)
 *   dn_prem   후보의 **첫 전제**                      → 후보      (`apply L in H`)
 *   dn_rw     후보 결론이 rewrite 관계면 **좌·우변**  → (후보, 변)
 *
 * 판별트리는 **상한**만 준다. 최종 판정은 `Unification.w_unify` — 커널이다.
 *
 * ## 후보의 범위
 *   전역 상수(`Environ.fold_constants`) + **귀납형·생성자**(`fold_inductives`)
 *   + **지역 가설**(`named_context`).  gold 의 12.7% 가 지역 가설이었다.
 *
 * ## rewrite 관계
 *   `eq`/`iff` 는 직접 본다. 그 밖은 `Rewrite.is_applied_rewrite_relation`
 *   (Sozeau, "A New Look at Generalized Rewriting in Type Theory", JFR 2009)
 *   에 물어본다 — Coq 의 `setoid_rewrite` 가 쓰는 바로 그 판정이다. *)

open Names
open Pp

(* ★ 결론까지 벗길 바인더 최대 개수. **암묵 인자도 바인더로 센다** —
   `forall {A} {B} (x y z : T) (H1 H2 : P), … -> concl` 이면 8을 넘는다.
   일반성의 실질적 상한이므로 조절 가능하게 둔다. *)
(* 실측(107지점×4): 4→65.4% · 8→88.8% · 12→92.5% · 20→93.5%.
   rewrite 는 12 에서 포화(54.2%), apply 만 20까지 더 오른다. 비용 +14% 후보 · +5% 시간. *)
(* ★ 검색 판본. **바꿀 때마다 올린다.** 모든 출력에 찍혀서
   "이 수치가 어느 판본 것인가" 를 나중에 되짚을 수 있게 한다.
   판본별 변경·실측은 all_log/docs/applicability/versions.md *)
let retrieval_version = "r15"

(* ★ 시동 자가검사 — 설정값이 서로 어긋나면 즉시 죽는다 *)
let () = assert (String.length retrieval_version >= 2)

(* ── ★ r11 : 채널 범위 ────────────────────────────────────────────────────
 * `ap · in · rw · rwh` 만 계산한다 — **진짜 검색이 필요한 것만**.
 *
 * `uf`·`ds`·`dc` 를 뺀 근거 (CompCert 315지점 실측, 단독 기여 = 그 채널을
 * 빼면 gold 을 아예 못 찾게 되는 지점 수):
 *
 *     채널   gold포함   단독기여   후보중앙
 *     ap       115        46        334
 *     in        70         9        618
 *     rw        88        47        418
 *     uf       109        75          7    ← 크지만 **검색이 아니다**
 *     ds         0         0          3    ← 귀납형 타입 이름. gold 이 된 적 0회
 *     dc        36         0        171    ← 찾는 것을 전부 다른 채널도 찾는다
 *
 *   uf 후보는 정의상 **goal·가설에 이미 보이는 이름**이다 (`terms` 를 훑는다).
 *   모델은 증명 상태를 이미 보고 있으므로 검색으로 줄 것이 없다 —
 *   "풀에 1.5% → 100%" 는 지표가 과장한 것이다.
 *   ds·dc 는 단독 기여가 0이면서 지점당 잡음 174개를 더한다.
 *
 * `ApplicWideChannels 1` 로 되살릴 수 있다. 코드는 그대로 있다. *)
let wide_channels = ref false

let max_arrows_r = ref 28
(* ★ 20→28 (2026-09-01): buchberger 텔레스코프(∀변수 12+ · 화살표 10+)가
   커널 Prod 22~26개라 결론까지 못 내려갔다 — TEST apply 자기채널 실패 7/7 의
   원인(전부 in 채널에만). arrows_sweep 실측: 12→20 비용 +11%로 평탄. *)
(* Section 변수 방출 때문에 커야 한다 — 실측 `match_stacks_inside_invariant` 는
   눈으로 13개인데 커널은 21개다. 그런데 시간이 여기에 비례한다. *)
let max_arrows () = !max_arrows_r

(* ── 후보 ─────────────────────────────────────────────────────────────── *)

type cand =
  | CConst of Constant.t
  | CCtor of constructor
  | CInd of inductive
  | CHyp of Id.t

let cand_name = function
  | CConst c -> Libnames.string_of_qualid
                  (Nametab.shortest_qualid_of_global Id.Set.empty (GlobRef.ConstRef c))
  | CCtor c -> Libnames.string_of_qualid
                 (Nametab.shortest_qualid_of_global Id.Set.empty (GlobRef.ConstructRef c))
  | CInd i -> Libnames.string_of_qualid
                (Nametab.shortest_qualid_of_global Id.Set.empty (GlobRef.IndRef i))
  | CHyp id -> Id.to_string id

(* ── 판별트리 ─────────────────────────────────────────────────────────── *)

module Key = struct
  type t = int * int                  (* (후보 번호, 깊이 또는 변) *)
  let compare (a1, b1) (a2, b2) =
    let c = Int.compare a1 a2 in if c <> 0 then c else Int.compare b1 b2
end

module DN = Btermdn.Make (Key)

(* ★ `None` 은 "전부 투명" 이라 트리가 거의 안 거른다(실측 raw 33,168 → 6,370).
   `Some TransparentState.empty` = 아무것도 펼치지 않음 = 최대 판별력. *)
(* ★ 절충점이다. `Some empty`(전부 경직) 는 좁고 빠르지만 **delta 변환이 필요한
   매칭을 놓친다**. `None` 은 완전에 가깝지만 넓다. 실측으로 고른다. *)
let rigid_mode = ref true
(* ★ 이분법이 아니다. Coq 의 hint DB 도 db 마다 투명도 집합을 들고 다니고
   `Hint Unfold f` 가 거기에 f 를 넣는다. Lean 4 의 `DiscrTree` 도 키를 만들 때
   `@[reducible]` 만 펼친다(`whnfR`). **막는 상수만** 투명으로 넣는다. *)
let extra_ts = ref TransparentState.empty
let ts () : TransparentState.t option =
  if !rigid_mode then Some !extra_ts else None

let add_transparent (c : Constant.t) =
  extra_ts := { !extra_ts with TransparentState.tr_cst = Cpred.add c (!extra_ts).TransparentState.tr_cst }

let clear_transparent () = extra_ts := TransparentState.empty

type hlab = HC of string | HI of string | HK of string | HV of string
          | HSort | HProd | HFlex

type index = {
  mutable apply : DN.t;
  mutable prem  : DN.t;
  mutable rw    : DN.t;
  mutable cands : cand array;
  mutable rawty : Constr.t array;     (* 값싼 선별용 선언 타입 *)
  mutable heads : hlab array array array; (* [i].(d) = 깊이 d 결론부 머리들 *)
  mutable nglob : int;
  mutable npat  : int;
  mutable build : float;
}

let idx = { apply = DN.empty; prem = DN.empty; rw = DN.empty;
            cands = [||]; rawty = [||]; heads = [||];
            nglob = -1; npat = 0; build = 0.0 }

(* ★ 색인 구축 뒤 불변식 — 조용한 빈 색인을 막는다 *)
let check_index () =
  assert (Array.length idx.cands = Array.length idx.rawty);
  assert (idx.npat >= 0);
  if Array.length idx.cands > 0 then
    assert (idx.npat > 0)     (* 후보가 있는데 패턴이 0이면 배선이 깨진 것 *)

let nb_globals env =
  Environ.fold_constants (fun _ _ n -> n + 1) env 0
  + Environ.fold_inductives (fun _ _ n -> n + 1) env 0

(* ── rewrite 관계 판정 ────────────────────────────────────────────────── *)

(* 결론이 rewrite 로 쓸 수 있는 관계 적용이면 좌·우변을 준다.
   ① `eq` / `iff` 는 직접 — 값싸다.
   ② 그 밖은 Coq 의 일반화 rewrite 판정에 물어본다(Sozeau 2009). *)
let use_setoid = ref true

(* ★ setoid 판정 캐시. `Rewrite.is_applied_rewrite_relation` 은 타입클래스
   해석을 돌리므로 비싸다 — 후보 12,652 × 깊이 8 = 10만 번을 부르면 메모리가
   터진다(실측 RSS 116GB·153GB, 좀비 coqtop 17개). 관계인지 여부는 사실상
   **머리 기호**로 정해지므로 머리로 캐시한다. *)
let setoid_cache : (string, bool) Hashtbl.t = Hashtbl.create 257

let head_name sigma t =
  match EConstr.kind sigma (fst (EConstr.decompose_app sigma t)) with
  | Constr.Const (c, _) -> Some ("c" ^ Constant.to_string c)
  | Constr.Ind (i, _) -> Some ("i" ^ MutInd.to_string (fst i) ^ string_of_int (snd i))
  | Constr.Var v -> Some ("v" ^ Id.to_string v)
  | _ -> None

(* 항이 지나치게 크면 건너뛴다 — 단일화·인쇄가 폭발하는 자리다. *)
let too_big sigma t =
  let n = ref 0 in
  let rec go x = incr n; if !n < 4000 then EConstr.iter sigma go x in
  go t; !n >= 4000

(* ★ 관계 결합자 화이트리스트 δ — `symmetric A eqA` 류 결론을 펼친다.
   buchberger 의 레코드 사영(`eqA_sym : … symmetric A eqA`)이 이 꼴이라
   A-트리가 `symmetric` 머리로 저장하고 goal 은 `eqA b a` 머리로 조회해
   영원히 어긋났다(dnA=0 실측). 전면 δ 는 mathcomp 에서 폭발했으므로
   **이 넷만** 편다 — 본체가 작은 ∀ 사슬이라 비용 유계. *)
let rel_whitelist = [
  "Coq.Relations.Relation_Definitions.symmetric";
  "Coq.Relations.Relation_Definitions.transitive";
  "Coq.Relations.Relation_Definitions.reflexive";
  "Coq.Relations.Relation_Definitions.antisymmetric";
]

let unfold_rel env sigma t =
  let (hd, _) = EConstr.decompose_app sigma t in
  match EConstr.kind sigma hd with
  | Constr.Const (c, _) when List.mem (Constant.to_string c) rel_whitelist ->
    let t' = Reductionops.whd_all env sigma t in
    if EConstr.eq_constr sigma t t' then None else Some t'
  | _ -> None

(* ★ iff 판별 — `apply L in H` 는 iff 결론 lemma 를 받는다 (proj 방향 자동).
   실측(VAL only_in): apply-in 자기채널 5실패 중 4가 iff (`or_comm`·
   `Nat.le_succ_l`·`Nat.lt_eq_cases`). eq/setoid 는 apply-in 대상이 아니므로
   rw_sides 를 안 쓰고 iff 만 좁게 본다. *)
let iff_sides sigma t =
  let (hd, args) = EConstr.decompose_app sigma t in
  let n = Array.length args in
  if n < 2 then None
  else match EConstr.kind sigma hd with
    (* ★ `and` 는 귀납형이지만 **`iff` 는 `Definition`(Const)** 이다 —
       concl_parts 주석에 이미 적어 놓고 Ind 로 맞춰서 한 번 헛돌았다. *)
    | Constr.Const (c, _) when Constant.to_string c = "Coq.Init.Logic.iff" ->
      Some (args.(n - 2), args.(n - 1))
    | _ -> None

let rw_sides env sigma (t : EConstr.t) =
  let (hd, args) = EConstr.decompose_app sigma t in
  let n = Array.length args in
  if n < 2 then None
  else
    let direct =
      match EConstr.kind sigma hd with
      | Constr.Ind (i, _) ->
        let nm = MutInd.to_string (fst i) in
        nm = "Coq.Init.Logic.eq" || nm = "Coq.Init.Logic.iff"
      | _ -> false
    in
    if direct then (assert (n >= 2); Some (args.(n - 2), args.(n - 1)))
    else if not !use_setoid then None
    else
      (* ★ setoid — `Rle`·`Znumtheory.rel_prime` 같은 사용자 관계도 `Proper`
         인스턴스가 있으면 `rewrite` 대상이다. Coq 에게 물어본다. *)
      match head_name sigma t with
      | None -> None
      | Some hk ->
        let ok =
          match Hashtbl.find_opt setoid_cache hk with
          | Some v -> v
          | None ->
            let v =
              (try (match Rewrite.is_applied_rewrite_relation env sigma [] t with
                    | Some _ -> true | None -> false)
               with e when CErrors.noncritical e -> false) in
            Hashtbl.replace setoid_cache hk v; v
        in
        if ok then Some (args.(n - 2), args.(n - 1)) else None

(* ★ ssreflect **묶음 규칙** — `Definition inE := (in_set, in_set1, inE).`
   타입이 등식이 아니라 `(P1 * P2 * P3)%type` 튜플이다. `rewrite inE` 는
   성분마다 재작성한다. 성분을 안 펴면 R 색인에 아예 못 들어간다 —
   실측(VAL/TEST mathcomp) 실패 gold 중 `inE` 가 **9건으로 최다**였다.
   `prod` 는 우결합이라 `(A,B,C)` 는 `A * (B * C)` 로 중첩된다. *)
(* ★ 반환에 **sigma 를 같이 준다.** 성분의 Π 를 벗기며 `new_evar` 로 evar 를
   만드는데, 그 sigma 를 안 돌려주면 호출부가 옛 sigma 로 그 항을 읽는다 →
   `Anomaly "in retyping: Unknown evar"`. 이 버그를 두 번째로 냈다. *)
(* ★ δ 전개가 **값이 있었나** 를 상수별로 기억한다.
   mathcomp 은 `associative`·`commutative`·`left_id` 처럼 등식을 감싼 정의를
   수천 번 재사용하는데, 값 없는 정의까지 매번 `whd_all` 하면 비싸다.
   실측: 캐시 없이 점당 9.1초 → 23.6초 (2.6배). *)
let delta_ok : (string, bool) Hashtbl.t = Hashtbl.create 97

(* ★ 정의 뒤에 숨은 등식을 δ 로 여는가. **기본 꺼짐.**
   mathcomp 은 등식을 래퍼 정의로 감싼다 (`mulrA : @associative R *%R`).
   열면 잡히지만 비싸다 — 실측(ssreflect 환경) 점당 2.0초 → 45.8초 (22배).
   R 색인이 403 → 635 로 불어 커널 단일화가 그만큼 는다.
   mathcomp 은 VAL/TEST 의 각 ~20% 이고 TRAIN 엔 **아예 없다**.
   그래서 기본은 끄고 `ApplicDelta 1` 로 켠다. *)
let iffp_dbg = ref 0        (* 디버그: iff→P 색인 성공 수 *)
let iffp_fail = ref 0       (* 디버그: iff 변 pat 실패 수 *)
let wca_dbg = ref 0         (* 디버그: 유연머리 결론 → Everything 색인 수 *)
let tap_dbg = ref 0.0       (* 구간 타이머: apply 루프 *)
let tin_dbg = ref 0.0       (* 구간 타이머: apply-in 루프 *)
let trw_dbg = ref 0.0       (* 구간 타이머: redex 수집+rewrite 루프 *)
let delta_unfold = ref false

(* ★ `~evars` — Π 를 벗을 때 evar 를 만들지 말지.
   색인 때는 **만들면 안 된다.** 후보 12,652개 × 깊이마다 부르는데 매번
   `new_evar` 를 하면 sigma 가 폭발한다 — 실측으로 coqtop 하나가 **215GB** 를
   먹고 기계를 마비시켰다. 패턴 생성(`constr_val_discr`)은 열린 `Rel` 을
   `Nothing`(=와일드카드)으로 처리하므로 **치환 없이 몸통으로 내려가면 된다**.
   검증 때는 실제 단일화를 해야 하므로 evar 가 필요하다 — 그때만 켠다.

   `inside` — 튜플 성분 안에서만 Π 를 벗긴다. 최상위에서 벗기면 바깥
   `index_cand.go` 의 하강과 겹쳐 중복 색인이 된다(raw 5배). *)
let rw_sides_all ?(evars = true) env sigma t =
  let acc = ref [] in
  let rec go inside d s t =
    if d > 12 then s else
    match (try rw_sides env s t with e when CErrors.noncritical e -> None) with
    | Some (l, r) -> acc := (l, r) :: !acc; s
    | None ->
      let (hd, args) = EConstr.decompose_app s t in
      (match EConstr.kind s hd with
       | Constr.Ind (i, _)
         when MutInd.to_string (fst i) = "Coq.Init.Datatypes.prod"
              && Array.length args = 2 ->
         let s1 = go true d s args.(0) in go true d s1 args.(1)
       (* mathcomp 은 등식을 정의 뒤에 숨긴다: `mulrA : @associative R *%R`.
          머리가 투명한 상수면 βδ 로 한 번 열고 다시 본다. 비싸서 기본 꺼짐. *)
       | Constr.Const (c, _)
         when !delta_unfold
              && (match Hashtbl.find_opt delta_ok (Constant.to_string c) with
                  | Some v -> v
                  | None ->
                    (match (Environ.lookup_constant c env).Declarations.const_body with
                     | Declarations.Def _ -> true
                     | _ -> false)) ->
         let ckey = Constant.to_string c in
         let before = List.length !acc in
         let t' = Reductionops.whd_all env s t in
         if EConstr.eq_constr s t t' then
           (Hashtbl.replace delta_ok ckey false; s)
         else begin
           let s2 = go true (d + 1) s t' in
           if not (Hashtbl.mem delta_ok ckey) then
             Hashtbl.replace delta_ok ckey (List.length !acc > before);
           s2
         end
       | _ when not inside -> s
       | _ ->
         (match EConstr.kind s t with
          | Constr.Prod (_, a, b) ->
            if evars then
              (try
                 let (s', ev) = Evarutil.new_evar env s a in
                 go inside (d + 1) s' (EConstr.Vars.subst1 ev b)
               with e when CErrors.noncritical e -> s)
            else
              (* ★ 치환하지 않는다. 열린 `Rel` 은 패턴에서 와일드카드가 된다. *)
              go inside (d + 1) s b
          | Constr.LetIn (_, a, _, b) -> go inside (d + 1) s (EConstr.Vars.subst1 a b)
          | Constr.Cast (c, _, _) -> go inside d s c
          | _ -> s))
  in
  let sg = go false 0 sigma t in
  let out = List.rev !acc in
  (* ★ 색인 경로(`evars=false`)는 sigma 를 **안 건드려야** 한다.
     건드리면 후보마다 evar 가 쌓여 폭발한다(실측 215GB). *)
  assert (evars || sg == sigma);
  (sg, out)

(* ── 색인 구축 ────────────────────────────────────────────────────────── *)

let print_types = ref false
let dn_depth = ref 2
(* 깊이 제한 검증(빠름) vs 모든 접미사 재검(느리지만 완전) *)
let exact_depth = ref true
(* ★ `apply` 를 판별트리로 좁히면 **delta 변환이 필요한 매칭을 놓친다**
   (실측 ap 적중 78.2% → 37.3%). 트리를 비경직으로 풀면 40배 느려진다
   (raw 29k → 519k, 710ms → 28.7s). 그래서 apply 만 선형 훑기로 되돌린다.
   값싼 머리-기호 선별로 거른 뒤 `w_unify`(delta 포함) 로 확정한다. *)
let apply_dn = ref false
(* rewrite 추상 타입검사 — 실제 `rewrite` 와 같은 조건 *)
let type_check_rw = ref true

let add_pat which p key =
  match which with
  | `A -> idx.apply <- DN.add idx.apply p key
  | `P -> idx.prem <- DN.add idx.prem p key
  | `R -> idx.rw <- DN.add idx.rw p key

(* 후보 하나를 색인에 넣는다. 전제를 evar 로 하나씩 채우며 내려간다 —
   접미사마다 새로 만들지 않으므로 evar 는 **바인더 수만큼**만 생긴다. *)
(* ── ★ 결론 분해 — `apply` 는 `/\` 와 `<->` 를 뚫고 들어간다 ──────────────
 * Coq 에 직접 물어 확인했다:
 *     Liff : n = 0 <-> n + 0 = 0   goal `3 + 0 = 0`   → `apply Liff`  OK
 *     Land : n + 0 = n /\ n * 1 = n goal `3 + 0 = 3`  → `apply Land`  OK
 *     (`rewrite Land` 은 NO — rewrite 는 안 뚫는다)
 * 우리는 결론 **전체**만 맞춰 봤으므로 이 둘을 통째로 놓쳤다. *)

let rec concl_parts sigma t =
  let (hd, args) = EConstr.decompose_app sigma t in
  let n = Array.length args in
  if n < 2 then [t]
  else
    (* ★ `and` 는 귀납형이지만 **`iff` 는 `Definition`** 이다
       (`iff A B := (A -> B) /\ (B -> A)`). Const 로 오므로 따로 봐야 한다 —
       이걸 놓쳐서 `apply Liff` 를 못 잡았다. *)
    let nm = match EConstr.kind sigma hd with
      | Constr.Ind (i, _) -> MutInd.to_string (fst i)
      | Constr.Const (c, _) -> Constant.to_string c
      | _ -> "" in
    if nm = "Coq.Init.Logic.and" || nm = "Coq.Init.Logic.iff" then
      t :: (concl_parts sigma args.(n - 2) @ concl_parts sigma args.(n - 1))
    else [t]

(* 결론이 **귀납형 적용**이고 그 인자가 goal 과 닿으면 destruct 대상이다.
   `Lex : forall n, exists m, m = n` 을 `destruct (Lex 3)` 로 쓰는 형태.
   (`sumbool`/`bool` 만 보던 판정 채널의 일반화다.) *)
let inductive_concl sigma t =
  let (hd, args) = EConstr.decompose_app sigma t in
  match EConstr.kind sigma hd with
  | Constr.Ind (i, _) when Array.length args > 0 -> Some (i, args)
  | _ -> None

(* ★ **결론이 `Prop` 인 것만 색인한다.** 기본 켜짐.
   A·P·R 트리는 `apply`/`rewrite` 전용이고, 그 gold 은 실측 **100% Prop** 이다
   (CompCert gold 284종 중 판정된 72개: apply 29/29 · rewrite 17/17 이 Prop).
   Prop 아닌 gold 18개는 전부 `uf`·`ds`·`dc` 채널 것인데, 그 셋은 색인을 안
   쓰고 goal 을 직접 훑으므로 영향이 없다 (`zle`·`peq` 는 `sumbool` = Set).

   노리는 것은 mathcomp 이다 — 후보 21,512개 중 `Order` 4,216개가 전부 HB
   배관(`__canonical__`·`__to__`·`.class`·`.pack_`·`Axioms_`)이고 Prop 이 아니다.
   `ApplicPropOnly 0` 으로 끈다. *)
let prop_only = ref true

(* `is_prop` 은 아래에 있으므로 여기서 쓸 작은 판정기를 따로 둔다 *)
let is_prop_ty env sigma ty =
  try Sorts.is_prop (EConstr.ESorts.kind sigma (Retyping.get_sort_of env sigma ty))
  with e when CErrors.noncritical e -> true

let index_cand env sigma (id : int) (ty : EConstr.t) =
  let pat sigma t =
    try Some (DN.constr_pattern env sigma (ts ()) t)
    with e when CErrors.noncritical e -> None in
  (* 결론까지 벗겨 sort 를 본다. evar 없이 — sort 만 보면 된다. *)
  let concl_sort_is_prop () =
    (* ★ 바인더를 **환경에 밀어 넣으며** 내려간다.
       치환 없이 `Rel` 을 열어 두고 `get_sort_of` 를 부르면
       `Anomaly "in retyping: Unbound local variable"` 이 난다.
       evar 를 만들면 색인에서 sigma 가 폭발한다(215GB 실측) — 그래서 push_rel. *)
    let rec cc n e t =
      if n > max_arrows () then (e, t)
      else match EConstr.kind sigma t with
        | Constr.Prod (na, a, b) ->
          let d = Context.Rel.Declaration.LocalAssum
                    (na, EConstr.Unsafe.to_constr a) in
          cc (n + 1) (Environ.push_rel d e) b
        | Constr.LetIn (na, v, a, b) ->
          let d = Context.Rel.Declaration.LocalDef
                    (na, EConstr.Unsafe.to_constr v, EConstr.Unsafe.to_constr a) in
          cc (n + 1) (Environ.push_rel d e) b
        | Constr.Cast (c, _, _) -> cc n e c
        | _ -> (e, t) in
    try
      let (e2, c) = cc 0 env ty in
      Sorts.is_prop (EConstr.ESorts.kind sigma (Retyping.get_sort_of e2 sigma c))
    with e when CErrors.noncritical e -> true   (* 모르면 넣는다 — 안전 쪽 *)
  in
  (* ★ 트리마다 조건이 다르다.
       A(결론) — `apply L` 의 결론이 goal 과 맞아야 하므로 **결론이 Prop**
       R(좌·우변) — `rw_sides` 가 eq/iff/setoid 만 통과시키므로 본래 Prop
       P(비의존 전제) — `apply L in H` 는 **전제**가 H 와 맞으면 된다.
                        결론은 아무거나 좋다. 결론으로 거르면 안 된다 —
                        실측으로 applyin 이 456 → 100 으로 무너졌다. *)
  let concl_prop = (not !prop_only) || concl_sort_is_prop () in
  let rec go n sigma t =
    (* ★ 결론이 `/\`·`<->` 면 그 부분도 apply 대상이다 *)
    if concl_prop then
      List.iter (fun part ->
          match pat sigma part with
          | Some p -> add_pat `A p (id, n); idx.npat <- idx.npat + 1
          | None ->
            (* ★ 매개변수 관계 결론 (`?eqA ?b ?a` — evar 머리+인자) 은 패턴화가
               실패해 **조용히 버려졌다** — buchberger `eqA_sym`·`eqTerm_trans`
               류 (TEST apply 자기채널 −11.6pp 의 몸통). 머리 evar 만으로
               Everything 색인해 조회엔 항상 나오게 하고, 걸러내기는 어차피
               커널 단일화가 한다. *)
            let (hd, args) = EConstr.decompose_app sigma part in
            if Array.length args > 0 then
              (match EConstr.kind sigma hd with
               | Constr.Evar _ | Constr.Rel _ ->
                 (match pat sigma hd with
                  | Some p ->
                    add_pat `A p (id, n); idx.npat <- idx.npat + 1;
                    incr wca_dbg
                  | None -> ())
               | _ -> ()))
        (concl_parts sigma t);
    (* rewrite 쪽 — 이 깊이의 결론이 관계면 좌·우변을 넣는다 *)
    (* ★ 깊이는 항상 다 본다. rewrite lemma 는 대개 전제가 있어 등식이 깊이 ≥1
       에 있다(`PTree.gso : i <> j -> get i (set j x m) = get i m`).
       `use_setoid` 는 **eq/iff 밖의 관계를 볼지**만 정한다 — 깊이와 무관하다. *)
    (* ★ 튜플 묶음 규칙이면 성분이 여럿이다. 태그에는 깊이·변만 싣고
       (성분 번호는 안 싣는다) 검증 때 성분을 다 훑는다 — 성분 수가 적어서
       그 편이 태그를 넓히는 것보다 싸다. *)
    (let (sg_rw, prs) = rw_sides_all ~evars:false env sigma t in
     List.iter (fun (l, r) ->
         List.iteri (fun i d -> match pat sg_rw d with
             | Some p ->
               assert (i = 0 || i = 1);           (* 좌변/우변 두 가지뿐 *)
               (* ★ 태그 = 깊이*2 + 변. 되꺼낼 때 `tag/2`·`tag mod 2` 로 푼다.
                 음수거나 깊이가 상한을 넘으면 `descend` 가 엉뚱한 데를 판다. *)
              assert (n >= 0 && n <= max_arrows ());
              assert (n * 2 + i >= 0 && (n * 2 + i) / 2 = n && (n * 2 + i) mod 2 = i);
              add_pat `R p (id, n * 2 + i); idx.npat <- idx.npat + 1
             | None -> ()) [l; r]) prs);
    (* ★ 이 깊이의 결론이 iff 면 **양변을 P 트리에도** 넣는다 — 태그는 깊이
       그대로. 질의쪽 descend 가 같은 깊이로 파고들어 iff 분기로 맞춘다. *)
    (match iff_sides sigma t with
     | Some (la, ra) ->
       List.iter (fun side -> match pat sigma side with
           | Some p ->
             add_pat `P p (id, n); idx.npat <- idx.npat + 1;
             incr iffp_dbg
           | None -> incr iffp_fail) [la; ra]
     | None -> ());
    if n >= max_arrows () then ()
    else
      match EConstr.kind sigma t with
      | Constr.Prod (_, a, b) ->
        (* ★ `apply L in H` 는 Coq 매뉴얼대로 **비의존 전제**를 오른쪽부터 맞춘다.
           첫 Prod 만 보면 안 된다 — 대개 `A : Type` 같은 암묵 인자다.
           (`PTree.gso : forall [A] [i j] x m, i <> j -> …` 의 첫 Prod 는 `A`) *)
        if EConstr.Vars.noccurn sigma 1 b
           && ((not !prop_only) || is_prop_ty env sigma a) then
          (match pat sigma a with
           | Some p -> add_pat `P p (id, n); idx.npat <- idx.npat + 1
           | None -> ());
        (try
           let (sigma, ev) = Evarutil.new_evar env sigma a in
           go (n + 1) sigma (EConstr.Vars.subst1 ev b)
         with e when CErrors.noncritical e -> ())
      | Constr.LetIn (_, a, _, b) -> go (n + 1) sigma (EConstr.Vars.subst1 a b)
      | Constr.Cast (c, _, _) -> go n sigma c
      | _ ->
        (match unfold_rel env sigma t with
         | Some t' -> incr wca_dbg; go n sigma t'
         | None -> ())
  in
  go 0 sigma ty

let build_index env sigma =
  Btermdn.dnet_depth := !dn_depth;
  let t0 = Unix.gettimeofday () in
  idx.apply <- DN.empty; idx.prem <- DN.empty; idx.rw <- DN.empty; idx.npat <- 0;
  let acc = ref [] in
  let push c = acc := c :: !acc in
  Environ.fold_constants (fun c _ () -> push (CConst c)) env ();
  (* ★ 귀납형과 **생성자** — `apply conj` · `apply or_introl` 을 놓치지 않는다 *)
  Environ.fold_inductives
    (fun mind mib () ->
       Array.iteri
         (fun i pk ->
            push (CInd (mind, i));
            Array.iteri (fun j _ -> push (CCtor ((mind, i), j + 1)))
              pk.Declarations.mind_consnames)
         mib.Declarations.mind_packets)
    env ();
  let arr = Array.of_list (List.rev !acc) in
  assert (Array.length arr > 0);
  idx.cands <- arr;
  idx.rawty <- Array.make (Array.length arr) Constr.mkProp;
  idx.heads <- Array.make (Array.length arr) [||];
  assert (Array.length idx.rawty = Array.length idx.cands);
  Array.iteri
    (fun i c ->
       try
         let gref = match c with
           | CConst k -> GlobRef.ConstRef k
           | CCtor k -> GlobRef.ConstructRef k
           | CInd k -> GlobRef.IndRef k
           | CHyp _ -> raise Exit in
         let (sg, tm) = Evd.fresh_global env sigma gref in
         let ty = Retyping.get_type_of env sg tm in
         idx.rawty.(i) <- EConstr.Unsafe.to_constr ty;
         if not (too_big sg ty) then index_cand env sg i ty
       with e when CErrors.noncritical e -> ())
    arr;
  idx.nglob <- nb_globals env;
  idx.build <- Unix.gettimeofday () -. t0;
  (* 색인이 비면 뒤 단계가 조용히 0 을 낸다 — 여기서 터뜨린다. *)
  assert (idx.npat > 0);
  assert (Array.length idx.rawty = Array.length idx.cands)

(* ── 판정 ─────────────────────────────────────────────────────────────── *)

(* ★ 같은 후보가 여러 조회에서 반복해 나온다. `fresh_global`+`get_type_of` 는
   싸지 않으므로 **지점마다 한 번**만 계산해 캐시한다. *)
let tycache : (int, (Evd.evar_map * EConstr.t) option) Hashtbl.t = Hashtbl.create 997

let cand_type_raw env sigma (c : cand) =
  match c with
  | CHyp _ -> None
  | CConst k -> (try
                   let (sg, tm) = Evd.fresh_global env sigma (GlobRef.ConstRef k) in
                   Some (sg, Retyping.get_type_of env sg tm)
                 with e when CErrors.noncritical e -> None)
  | CCtor k -> (try
                  let (sg, tm) = Evd.fresh_global env sigma (GlobRef.ConstructRef k) in
                  Some (sg, Retyping.get_type_of env sg tm)
                with e when CErrors.noncritical e -> None)
  | CInd k -> (try
                 let (sg, tm) = Evd.fresh_global env sigma (GlobRef.IndRef k) in
                 Some (sg, Retyping.get_type_of env sg tm)
               with e when CErrors.noncritical e -> None)

let cand_type_i env sigma i c =
  assert (i >= 0);
  match Hashtbl.find_opt tycache i with
  | Some v -> v
  | None -> let v = cand_type_raw env sigma c in Hashtbl.replace tycache i v; v

(* ★ `apply`/`eapply` 는 `Unification.elim_flags ()` 를 쓴다. 기본 플래그는
   `?P ?n` 같은 **이차 패턴**을 못 풀어서 귀납원리(`N.binary_ind`)·Morphism
   (`Equivalence.equiv_symmetric`)을 통째로 놓쳤다 — 실측 위음성 7.0%. *)
let unify_ap env sigma a b =
  try let _ = Unification.w_unify env sigma Conversion.CONV
      ~flags:(Unification.elim_flags ()) a b in true
  with e when CErrors.noncritical e -> false

let unify1 env sigma a b =
  try let _ = Unification.w_unify env sigma Conversion.CONV a b in true
  with e when CErrors.noncritical e -> false

(* ★ 판별트리가 **몇 번째 화살표에서 맞았는지**(깊이)를 키에 실어 준다.
   그 깊이만 확인하면 된다 — 8단을 다시 훑으면 단일화가 8배로 든다.
   (Coq 의 hint DB 도 같은 이유로 패턴마다 진입점을 들고 다닌다.) *)
let descend env sigma ty d =
  let rec go n sigma t =
    if n >= d then Some (sigma, t)
    else
      match EConstr.kind sigma t with
      | Constr.Prod (_, a, b) ->
        (try
           let (sigma, ev) = Evarutil.new_evar env sigma a in
           go (n + 1) sigma (EConstr.Vars.subst1 ev b)
         with e when CErrors.noncritical e -> None)
      | Constr.LetIn (_, a, _, b) -> go (n + 1) sigma (EConstr.Vars.subst1 a b)
      | Constr.Cast (c, _, _) -> go n sigma c
      | _ ->
        (match unfold_rel env sigma t with
         | Some t' -> go n sigma t'
         | None -> None)
  in go 0 sigma ty

(* ★ 바인더를 벗기며 rewrite 관계를 찾는다.
   전역 후보는 색인 때 깊이별로 넣지만, **지역 가설**은 그러지 않았다 —
   `rw_sides` 를 타입에 바로 불렀다. 귀납 가설은 `forall …, a = b` 라
   머리가 `Prod` 이고, 그래서 `IHcases`·`IHl` 을 통째로 놓쳤다. *)
let dig_sides env sigma ty =
  let rec go n sigma t =
    match rw_sides_all env sigma t with
    | (sg2, (l, r) :: _) -> Some (sg2, l, r)
    | (_, []) ->
      if n >= max_arrows () then None
      else
        match EConstr.kind sigma t with
        | Constr.Prod (_, a, b) ->
          (try
             let (sigma, ev) = Evarutil.new_evar env sigma a in
             go (n + 1) sigma (EConstr.Vars.subst1 ev b)
           with e when CErrors.noncritical e -> None)
        | Constr.LetIn (_, a, _, b) -> go (n + 1) sigma (EConstr.Vars.subst1 a b)
        | Constr.Cast (c, _, _) -> go n sigma c
        | _ -> None
  in go 0 sigma ty

let unifies_at env sigma target ty d =
  assert (d >= 0 && d <= max_arrows ());
  match descend env sigma ty d with
  | None -> false
  | Some (sg, t) -> unify1 env sg t target

let unifies_upto env sigma target ty =
  let rec go n sigma t =
    if List.exists (fun part -> unify_ap env sigma part target)
        (concl_parts sigma t) then true
    else if n >= max_arrows () then false
    else
      match EConstr.kind sigma t with
      | Constr.Prod (_, a, b) ->
        (try
           let (sigma, ev) = Evarutil.new_evar env sigma a in
           go (n + 1) sigma (EConstr.Vars.subst1 ev b)
         with e when CErrors.noncritical e -> false)
      | Constr.LetIn (_, a, _, b) -> go (n + 1) sigma (EConstr.Vars.subst1 a b)
      | Constr.Cast (c, _, _) -> go n sigma c
      | _ -> false
  in go 0 sigma ty

let local_hyps env =
  List.filter_map
    (fun d ->
       let open Context.Named.Declaration in
       match d with
       | LocalAssum (na, ty) -> Some (na.Context.binder_name, EConstr.of_constr ty)
       | LocalDef (na, _, ty) -> Some (na.Context.binder_name, EConstr.of_constr ty))
    (Environ.named_context env)

(* 값싼 선별 — lemma 타입의 어떤 화살표 접미사 머리가 goal 머리와 맞나. *)
let head_key sigma t =
  EConstr.kind sigma (fst (EConstr.decompose_app sigma t))

let rigid_head sigma t =
  match head_key sigma t with
  | Constr.Const _ | Constr.Ind _ | Constr.Construct _ | Constr.Var _ | Constr.Sort _ -> true
  | _ -> false

(* ★ `Prod` 에 **고유 라벨**을 준다.
   예전 판은 `Prod` 의 머리를 유연으로 봤다 — `decompose_app` 이 Prod 를 그대로
   돌려주니 Const/Ind/… 중 무엇도 아니어서 "유연" 으로 떨어졌고, 그래서
   **모든 후보가 선별을 통과**했다(실측 keypass 11,222/11,766 = 95%).
   깊이 0 에서는 거의 모든 lemma 가 `forall …` 이므로 선별이 통째로 무용지물이었다. *)

let hlabel sigma t =
  match EConstr.kind sigma t with
  | Constr.Prod _ -> HProd
  | _ ->
    match EConstr.kind sigma (fst (EConstr.decompose_app sigma t)) with
    | Constr.Const (c, _) -> HC (Constant.to_string c)
    | Constr.Ind (i, _) -> HI (MutInd.to_string (fst i) ^ "/" ^ string_of_int (snd i))
    | Constr.Construct (((m, i), j), _) ->
      HK (MutInd.to_string m ^ "/" ^ string_of_int i ^ "/" ^ string_of_int j)
    | Constr.Var v -> HV (Id.to_string v)
    | Constr.Sort _ -> HSort
    | _ -> HFlex

let hcompat a b = match a, b with
  | HFlex, _ | _, HFlex -> true
  | x, y -> x = y

(* ★ 한쪽 머리가 **유연**하면 통과시킨다. `False_ind : forall P, False -> P` 의
   결론은 `?P` 라 아무 goal 에나 적용된다 — 배제하면 재현율을 잃는다. *)
let same_head sigma a b =
  if not (rigid_head sigma a) || not (rigid_head sigma b) then true
  else match head_key sigma a, head_key sigma b with
    | Constr.Const (x, _), Constr.Const (y, _) -> Constant.CanOrd.equal x y
    | Constr.Ind (x, _), Constr.Ind (y, _) -> Ind.CanOrd.equal x y
    | Constr.Construct (x, _), Constr.Construct (y, _) -> Construct.CanOrd.equal x y
    | Constr.Var x, Constr.Var y -> Id.equal x y
    | Constr.Sort _, Constr.Sort _ -> true
    | _ -> false

(* ★ **머리가 맞는 깊이만** 돌려준다 (예전엔 bool 하나였다).
   `depth_of` 가 0~max_arrows 를 전부 단일화하는데, `suffix_compat` 은
   "어느 한 깊이라도 맞나" 만 보고 통과시켰다 — 즉 **머리가 안 맞는 깊이까지
   커널 단일화를 돌렸다.** 같은 술어를 깊이별로 적용하는 것이라 재현율은
   그대로고(집합이 같다), 단일화 횟수만 준다.
   실측(CompCert): keypass 5,821 중 apply 성공 349 = 6%. 94%가 헛수고였다. *)
(* ★ 깊이별 결론부 머리 라벨 — rawty 는 정적이라 **색인 때 1회** 뽑는다.
   예전엔 goal 마다 12k 후보 전부의 타입을 다시 걸었다(EConstr 순회+
   concl_parts) — ap 구간 166ms 의 몸통. 지금 goal 쪽은 배열 비교뿐이다. *)
let head_labels env sigma ty =
  let out = ref [] in
  let rec go n t =
    let hs = List.map (hlabel sigma) (concl_parts sigma t) in
    out := (n, Array.of_list hs) :: !out;
    if n >= max_arrows () then ()
    else match EConstr.kind sigma t with
      | Constr.Prod (_, _, b) -> go (n + 1) b
      | Constr.LetIn (_, _, _, b) -> go (n + 1) b
      | Constr.Cast (c, _, _) -> go n c
      | _ ->
        (match unfold_rel env sigma t with
         | Some t' -> go n t'
         | None -> ())
  in go 0 ty;
  (* ★ unfold_rel 경로는 같은 깊이 n 을 두 번 방문한다 — 깊이별로 **병합**
     해야 배열 인덱스=깊이가 유지된다 (안 하면 이후 깊이가 +1 밀린다.
     실측: preord_trans new=[9] old=[8] 류 DSDIFF 전부 이것). *)
  let mx = List.fold_left (fun a (n, _) -> max a n) 0 !out in
  let arr = Array.make (mx + 1) [] in
  List.iter (fun (n, hs) -> arr.(n) <- Array.to_list hs @ arr.(n)) !out;
  Array.map Array.of_list arr

let suffix_from_heads heads gl =
  let acc = ref [] in
  Array.iteri (fun n hs ->
      if Array.exists (fun h -> hcompat h gl) hs then acc := n :: !acc) heads;
  List.rev !acc

let suffix_depths env sigma ty concl =
  let gl = hlabel sigma concl in
  let acc = ref [] in
  let rec go n t =
    (* 결론이 `/\`·`<->` 면 그 부분의 머리도 본다.
       예전 판은 `A /\ B` 의 머리를 `and` 로만 봐서 goal 이 `A` 인 경우를
       선별에서 잘라 버렸다(`apply Land` 를 놓쳤다). *)
    if List.exists (fun part -> hcompat (hlabel sigma part) gl)
        (concl_parts sigma t) then acc := n :: !acc;
    if n >= max_arrows () then ()
    else match EConstr.kind sigma t with
      | Constr.Prod (_, _, b) -> go (n + 1) b
      | Constr.LetIn (_, _, _, b) -> go (n + 1) b
      | Constr.Cast (c, _, _) -> go n c
      | _ ->
        (match unfold_rel env sigma t with
         | Some t' -> go n t'
         | None -> ())
  in go 0 ty;
  let out = List.rev !acc in
  (* ★ 깊이는 오름차순·범위 안·중복 없음. `try_apply` 가 `List.mem` 으로 쓰므로
     여기가 깨지면 조용히 후보를 건너뛴다. *)
  assert (List.for_all (fun d -> d >= 0 && d <= max_arrows ()) out);
  assert (List.length out = List.length (List.sort_uniq compare out));
  out

let suffix_compat env sigma ty concl = suffix_depths env sigma ty concl <> []

(* ★ `apply L in H` 는 H 가 **명제**여야 한다. `A : Type` · `i : positive` 같은
   데이터 가설로 첫-전제 색인을 조회하면 그 타입을 전제로 받는 lemma 가 전부
   나와 폭발한다(실측 applyin 4,820). Prop 인 가설만 전방추론 대상으로 삼는다. *)
let is_prop env sigma ty =
  try Sorts.is_prop (EConstr.ESorts.kind sigma (Retyping.get_sort_of env sigma ty))
  with e when CErrors.noncritical e -> false

let key_of sigma t =
  match EConstr.kind sigma (fst (EConstr.decompose_app sigma t)) with
  | Constr.Const _ | Constr.Ind _ | Constr.Construct _ | Constr.Var _ -> true
  | _ -> false

(* ★ 부분항 중복 제거용. 같은 부분항이 goal 안에 여러 번 나오면 그만큼
   반복 조회·반복 단일화가 된다 — 비용만 손해다. *)
module CH = Hashtbl.Make (struct
    type t = Constr.t
    let equal = Constr.equal
    let hash = Constr.hash
  end)

(* ★ 본체를 함수로 뺀다 — `applic_filter` 와 `applic_check` 가 **같은 코드**를
   쓰게 해야 진단이 실제 파이프라인과 어긋나지 않는다. 예전 진단은 `apply` 를
   판별트리로 재고 있었는데 apply 는 선형 훑기를 쓴다(측정 자체가 틀렸다). *)

(* ── ★ 랭킹 신호 · 타입 기반 추가 필터 ────────────────────────────────────
 *
 * ## 랭킹 (문헌)
 * 항은 포섭(subsumption)에 대해 **격자**를 이룬다.
 *   join = 단일화(mgu)      <- 우리 **필터**: g ⊔ c 가 존재하는가
 *   meet = 반단일화(lgg)    <- 우리 **랭커**: g ⊓ c 가 얼마나 큰가
 * (Plotkin 1970 · Reynolds 1970; Cerna & Kutsia, IJCAI 2023 개관)
 * 필터와 랭커가 한 대수 구조 안에서 쌍대(dual)로 설명된다.
 *
 * 파이프라인이 **이미 계산해 둔** 신호도 같이 낸다:
 *   d  매칭 깊이   — 트리가 어디까지 판별했나
 *   e  evar 개수   — eapply 가 몇 개를 추측해야 했나 (적을수록 goal 이 결정)
 *   z  redex 크기  — rewrite 가 goal 의 얼마를 건드리나
 *
 * ## 타입 기반 추가 필터 (rewrite 거짓양성 35.8% 를 겨냥)
 * `rewrite L` 은 redex 를 goal 에서 **추상화**해 fun x => C[x] 를 만든 뒤
 * eq_ind 류로 옮긴다. 그 추상이 **타입이 안 맞으면**(redex 가 의존 자리에
 * 있으면) rewrite 는 실패한다. 우리는 "좌변이 redex 와 단일화된다" 까지만
 * 보고 그 다음을 안 봤다 — 실측 정밀도 64.2% 의 자리다. *)

let rec term_size sigma t =
  let n = ref 1 in
  EConstr.iter sigma (fun x -> n := !n + term_size sigma x) t; !n

let rec lgg_size sigma a b =
  let (ha, aa) = EConstr.decompose_app sigma a in
  let (hb, ab) = EConstr.decompose_app sigma b in
  if Array.length aa = Array.length ab && EConstr.eq_constr sigma ha hb then begin
    let n = ref 1 in
    Array.iteri (fun i x -> n := !n + lgg_size sigma x ab.(i)) aa; !n
  end else 1

let abstract_ok env sigma target st =
  try
    let ty = Retyping.get_type_of env sigma st in
    let body = Termops.subst_term sigma st target in
    let lam = EConstr.mkLambda
        (Context.annotR (Names.Name.Name (Names.Id.of_string "x")), ty, body) in
    let _ = Typing.type_of env sigma lam in
    true
  with e when CErrors.noncritical e -> false


(* ── ★ 채널 확장: unfold · destruct ──────────────────────────────────────
 * 실측(CompCert rand200, 2,899 스텝): 외부 이름을 쓰는 스텝이 50.5% 인데
 * 그중 apply+rewrite 는 54.2% 뿐이다. 나머지 큰 덩어리가
 *   destruct 17.1% · unfold 10.2% · induction/case/elim 4.3% · exact 2.3%
 * 이다. 앞의 둘은 **goal 만 보면 정확히 결정된다** — 추측이 필요 없다.
 *
 *   unfold f   : f 가 goal/가설에 **나타나고** 펼칠 수 있어야 한다
 *   destruct t : t 의 **타입이 귀납형**이어야 한다
 *
 * exact 는 별도 채널이 필요 없다 — `apply` 중 **evar 가 0개**인 것이다
 * (우리가 이미 `e=` 로 세고 있다). *)

let unfoldable env c =
  match (Environ.lookup_constant c env).Declarations.const_body with
  | Declarations.Def _ -> true
  | _ -> false

(* goal·가설에 나타나는 상수 중 펼칠 수 있는 것 *)
let unfold_cands env sigma terms =
  let seen = Hashtbl.create 97 in
  let rec go t =
    (match EConstr.kind sigma (fst (EConstr.decompose_app sigma t)) with
     | Constr.Const (c, _) ->
       let k = Constant.to_string c in
       if not (Hashtbl.mem seen k) then
         Hashtbl.replace seen k (if unfoldable env c then Some c else None)
     | _ -> ());
    EConstr.iter sigma go t in
  List.iter go terms;
  Hashtbl.fold (fun _ v acc -> match v with Some c -> c :: acc | None -> acc) seen []

(* goal·가설의 닫힌 부분항 중 **타입이 귀납형**인 것 → 그 귀납형 이름 *)
let destruct_cands env sigma terms =
  let seen = Hashtbl.create 97 in
  let rec go t =
    (if EConstr.Vars.closed0 sigma t then
       match (try Some (Retyping.get_type_of env sigma t)
              with e when CErrors.noncritical e -> None) with
       | Some ty ->
         (match EConstr.kind sigma (fst (EConstr.decompose_app sigma ty)) with
          | Constr.Ind (i, _) ->
            let k = MutInd.to_string (fst i) ^ "/" ^ string_of_int (snd i) in
            if not (Hashtbl.mem seen k) then Hashtbl.replace seen k i
          | _ -> ())
       | None -> ());
    EConstr.iter sigma go t in
  List.iter go terms;
  Hashtbl.fold (fun _ i acc -> i :: acc) seen []



(* ── ★ 판정(decidability) 채널 ────────────────────────────────────────────
 * `case (zle (fst i) x)` 에서 `zle` 는 **goal 에 나타나지 않는다**. goal 에
 * 있는 것은 `Z.le` 이고, 필요한 연결은 "`Z.le` 를 판정하는 sumbool 함수".
 * 즉 결론이 `{P} + {~P}` 또는 `sumbool`/`bool` 이고 그 P 의 머리가 goal 에
 * 나타나는 상수를 모은다. 실측(rand200)에서 `case` 12건 전부와
 * `destruct (f …)` 상당수가 이 형태다. *)

let goal_heads env sigma terms =
  let h = Hashtbl.create 97 in
  let rec go t =
    (match EConstr.kind sigma (fst (EConstr.decompose_app sigma t)) with
     | Constr.Const (c, _) -> Hashtbl.replace h ("c" ^ Constant.to_string c) ()
     | Constr.Ind (i, _) ->
       Hashtbl.replace h ("i" ^ MutInd.to_string (fst i) ^ string_of_int (snd i)) ()
     | _ -> ());
    EConstr.iter sigma go t in
  List.iter go terms; h

let decide_cands env sigma terms =
  let gh = goal_heads env sigma terms in
  (* 단일화 상대가 될 goal 부분항 — 경직 머리에 닫힌 것만 *)
  let gsubs =
    let acc = ref [] in
    let rec go t =
      (if rigid_head sigma t && EConstr.Vars.closed0 sigma t then acc := t :: !acc);
      EConstr.iter sigma go t in
    List.iter go terms; !acc in
  ignore gh;
  let out = ref [] in
  Array.iteri
    (fun i c ->
       if i < Array.length idx.rawty then
         match c with
         | CConst k ->
           let ty = EConstr.of_constr idx.rawty.(i) in
           (* 결론까지 벗긴다 *)
           let rec concl n t =
             if n > max_arrows () then t
             else match EConstr.kind sigma t with
               | Constr.Prod (_, _, b) -> concl (n + 1) b
               | Constr.LetIn (_, _, _, b) -> concl (n + 1) b
               | Constr.Cast (x, _, _) -> concl n x
               | _ -> t in
           let cc = concl 0 ty in
           let (hd, args) = EConstr.decompose_app sigma cc in
           (match EConstr.kind sigma hd with
            | Constr.Ind (ind, _) ->
              let nm = MutInd.to_string (fst ind) in
              (* ★ `sumbool`/`bool` 만 보면 안 된다. `destruct (L a b)` 는
                 결론이 **어떤 귀납형이든** 된다 — `exists`·`\/`·`/\`·spec 류.
                 실측에서 `prog_defmap_linkorder`(결론이 존재) ·
                 `Pos.compare_spec`(결론이 3분기 귀납형)을 놓쳤다. *)
              if Array.length args > 0
              && nm <> "Coq.Init.Logic.eq" then begin
                (* 인자 안의 머리가 goal 에 있나 *)
                (* ★ **머리만 겹치면 통과** 시키던 것을 조인다.
                   그러면 후보가 107 → 490 으로 불고 `destruct` @10 이
                   52% → 46% 로 오히려 떨어졌다(신호가 못 가름).
                   결론 인자가 goal 의 부분항과 **실제로 단일화**되어야 한다 —
                   `destruct (peq r1 r2)` 는 `r1`·`r2` 가 goal 에 있어야 뜻이 있다. *)
                let ok = ref false in
                Array.iter (fun x ->
                    if not !ok && rigid_head sigma x then
                      List.iter (fun st ->
                          if not !ok && same_head sigma x st
                             && unify1 env sigma x st then ok := true)
                        gsubs) args;
                if !ok then out := k :: !out
              end
            | _ -> ())
         | _ -> ())
    idx.cands;
  !out






(* ── ★ Baire 초거리 — 판별트리 자신의 거리 ────────────────────────────────
 *
 * 판별트리는 항을 **전위 순회 문자열**로 보는 트라이다(Coq `btermdn.ml` 의
 * `constr_val_discr` 가 정확히 그 문자열을 만든다). 트라이 위의 자연스러운
 * 거리는 **최장 공통 접두사(LCP)** 로 정의되는 Baire 거리이고, 이것은
 * 단순한 거리가 아니라 **초거리(ultrametric)** 다:
 *
 *     d(s,t) = 2^(-LCP(s,t))        d(s,u) <= max(d(s,t), d(t,u))
 *
 * 즉 "트라이에서 goal 과 **가장 늦게 갈라지는** 후보" 가 가장 가깝다.
 * 필터가 트리를 **집합 연산**(어느 가지에 있나)으로 쓰는데, 같은 트리가
 * **거리**도 준다 — 그 거리를 랭킹에 쓴다. 자료구조를 하나 더 만들 필요가 없다.
 *
 * 이것은 포섭 격자의 meet(lgg)과 같은 것을 보는 두 가지 방식이다:
 *   lgg  항 수준의 공유 구조   (Plotkin 1970)
 *   LCP  문자열 수준의 공유 접두사 (Baire 거리)
 * lgg 가 더 정밀하고, LCP 는 트리가 이미 계산하는 것이다. 둘 다 낸다. *)

let rec preorder sigma depth acc t =
  if depth > 12 then acc
  else
    let (hd, args) = EConstr.decompose_app sigma t in
    let lab = match EConstr.kind sigma hd with
      | Constr.Const (c, _) -> "c" ^ Constant.to_string c
      | Constr.Ind (i, _) -> "i" ^ MutInd.to_string (fst i) ^ string_of_int (snd i)
      | Constr.Construct (((m, i), j), _) ->
        "k" ^ MutInd.to_string m ^ string_of_int i ^ "_" ^ string_of_int j
      | Constr.Var v -> "v" ^ Id.to_string v
      | Constr.Sort _ -> "s"
      | Constr.Prod _ -> "P"
      | Constr.Lambda _ -> "L"
      | _ -> "*" in
    let acc = lab :: acc in
    Array.fold_left (fun a x -> preorder sigma (depth + 1) a x) acc args

let preorder_of sigma t = Array.of_list (List.rev (preorder sigma 0 [] t))

(* ★ **구조적 IDF** — 말뭉치를 안 세고 lemma 모양에서 유도한다.

   `applic-idf(L) = −log₂ P(L 이 필터를 통과)` 는 이름별 조회표라 스플릿을
   넘어가면 항목이 없다(실측: 미관측 gold 이 −4.60 감점을 먹어 @10 −10pp).
   그런데 그 확률은 셀 필요가 없다 — **L 의 일반성**에서 나온다.

     격자:  필터 = join(mgu). 더 일반적인 항이 더 많은 goal 을 포섭한다.
     Baire: 가지치기 계수 b 인 트라이에서 k층까지 경직이면 b^(−k) 만 살아남는다.

   두 개를 이으면
       P̂(통과) ≈ b^(−rig)      rig = 전위 순회 라벨 중 **경직**(`*` 아님) 개수
       Î(L) = −log₂ P̂ = rig · log₂ b

   `f_equal : ?f ?x = ?f ?y` 는 머리가 유연해 rig 가 작고,
   `PTree.gso` 는 `get`·`set` 이 박혀 있어 rig 가 크다.
   판별트리가 이미 만드는 열이라 새로 계산할 것이 없다. *)
let rigidity (a : string array) =
  Array.fold_left (fun n x -> if x = "*" then n else n + 1) 0 a

(* 최장 공통 접두사 길이. `*`(유연) 은 무엇과도 맞는다 — 트리의 Everything 과 같다. *)
let lcp (a : string array) (b : string array) =
  let n = min (Array.length a) (Array.length b) in
  let i = ref 0 in
  while !i < n && (a.(!i) = b.(!i) || a.(!i) = "*" || b.(!i) = "*") do incr i done;
  !i


let compute gl =
      let env = Proofview.Goal.env gl in
      let sigma = Proofview.Goal.sigma gl in
      let concl = Proofview.Goal.concl gl in
      if idx.nglob <> nb_globals env then (build_index env sigma; check_index ());
      assert (Array.length idx.cands = Array.length idx.rawty);
      Hashtbl.reset tycache;
      let t0 = Unix.gettimeofday () in
      let hyps = local_hyps env in
      (* ★ in 채널 신호 — (전제 rig, 가설과의 lcp, lgg 크기).
         예전엔 APPLICIN 이 신호 없이 이름만 내보내 랭킹이 장님이었다. *)
      let sig_in : (string, int * int * int) Hashtbl.t = Hashtbl.create 97 in
      let out_ap = Hashtbl.create 97 and out_in = Hashtbl.create 97
      and out_rw = Hashtbl.create 97 in
      (* ★ `rewrite L` 과 `rewrite L in H` 는 **서로 다른 술어**다.
         실측: goal redex 로 통과 163 · 가설 redex 로만 통과 147 · **교집합 0**.
         비중도 6배 다르다(22.1% vs 3.8%). 한 채널로 묶으면 슬롯 배분이 어긋난다. *)
      let out_rwh = Hashtbl.create 97 in
      (* 랭킹 신호를 후보별로 모아 둔다 — lgg 크기 · evar 수 · redex 크기 · 깊이 *)
      let sig_ap : (string, int * int * int * int) Hashtbl.t = Hashtbl.create 97 in
      let gpre = preorder_of sigma concl in
      (* ★ rewrite 도 Baire LCP 를 잰다 — 좌·우변과 **맞은 redex** 사이.
         예전 판은 apply 에만 lcp 를 실어서, rewrite gold 은 신호가 0 이었다.
         `nm` = 이 lemma 가 맞은 redex 개수. 하나만 맞으면 특정적이고,
         여러 개 맞으면 그만큼 덜 특정적이다(= 정보가 적다). *)
      let sig_rw : (string, int * int * int * int * int * int) Hashtbl.t = Hashtbl.create 97 in
      (* ★ 가설 rewrite 는 신호를 **따로** 모은다 — (z, d, lcp, nm, 가설크기, 가설위치) *)
      let sig_rwh : (string, int * int * int * int * int * int * int) Hashtbl.t =
        Hashtbl.create 97 in
      let raw = ref 0 and keypass = ref 0 in
      let lookup dn t =
        try let l = DN.lookup env sigma (ts ()) dn t in raw := !raw + List.length l; l
        with e when CErrors.noncritical e -> [] in

      let _t_ap0 = Unix.gettimeofday () in
      (* ── ① apply ── *)
      (* ★ `ds` = 머리가 맞는 깊이 목록. 그 깊이에서만 단일화한다.
         나머지 깊이는 `suffix_depths` 가 이미 머리로 배제했으므로
         단일화해도 절대 안 맞는다 — 재현율 손실 없이 횟수만 준다. *)
      let try_apply ?ds i c =
        let nm = cand_name c in
        if not (Hashtbl.mem out_ap nm) then
          match cand_type_i env sigma i c with
          | Some (sg, ty) ->
            let want n = match ds with None -> true | Some l -> List.mem n l in
            (* 몇 단계 벗겨야 맞는지 = eapply 가 추측해야 하는 evar 개수 *)
            (* ★ evar 를 만든 sigma 를 **계속 들고 가야** 한다.
               버리고 옛 sigma 로 진행하면 `Unknown evar` 이상종료가 난다. *)
            let rec depth_of n sg t =
              if n > max_arrows () then None
              else match (if want n then
                            List.find_opt (fun part -> unify_ap env sg part concl)
                              (concl_parts sg t)
                          else None) with
                | Some part -> Some (n, sg, part)
                | None ->
              match EConstr.kind sg t with
                | Constr.Prod (_, a, b) ->
                  (try
                     let (sg, ev) = Evarutil.new_evar env sg a in
                     depth_of (n + 1) sg (EConstr.Vars.subst1 ev b)
                   with e when CErrors.noncritical e -> None)
                | Constr.LetIn (_, a, _, b) ->
                  depth_of (n + 1) sg (EConstr.Vars.subst1 a b)
                | Constr.Cast (c, _, _) -> depth_of n sg c
                | _ ->
                  (* ★ 관계 결합자(δ 화이트리스트) 를 펴고 계속 —
                     색인·descend 와 같은 규칙이어야 태그 깊이가 맞는다 *)
                  (match unfold_rel env sg t with
                   | Some t' -> depth_of n sg t'
                   | None -> None) in
            (match depth_of 0 sg ty with
             | Some (nev, sg2, cty) ->
               Hashtbl.replace out_ap nm ();
               (* lgg 크기 = goal 과 결론이 공유하는 구조 (포섭 격자의 meet) *)
               let cpre = preorder_of sg2 cty in
               Hashtbl.replace sig_ap nm
                 (lgg_size sg2 concl cty, nev, lcp gpre cpre, rigidity cpre)
             | None -> ())
          | None -> () in
      if not !apply_dn then
        (* 선형 훑기 — 머리 기호가 맞는 것만 단일화한다 *)
        (* ★ **선별을 먼저** 한다. 예전 판은 12,652개 전부에 `fresh_global`
           +`get_type_of` 를 돌린 **뒤에** 걸렀다 — 거꾸로였다. 선언 타입은
           색인 구축 때 받아 뒀으니 그걸로 머리를 먼저 본다. *)
        let _gl = hlabel sigma concl in
        Array.iteri
          (fun i c ->
             if i < Array.length idx.heads then begin
               (* ★ 지연 계산 — rawty 는 정적이라 정리당 첫 goal 에서 1회 *)
               if Array.length idx.heads.(i) = 0 then
                 (idx.heads.(i) <-
                    (try head_labels env sigma
                           (EConstr.of_constr idx.rawty.(i))
                     with e when CErrors.noncritical e -> [| [||] |]));
               (match suffix_from_heads idx.heads.(i) _gl with
               | [] -> ()
               | ds -> incr keypass; try_apply ~ds i c)
             end)
          idx.cands
      else
      List.iter
        (fun (i, d) ->
           if i >= 0 && i < Array.length idx.cands then
             let c = idx.cands.(i) in
             let nm = cand_name c in
             if not (Hashtbl.mem out_ap nm) then
               match cand_type_i env sigma i c with
               | Some (sg, ty) ->
                 if (if !exact_depth then unifies_at env sg concl ty d
                     else unifies_upto env sg concl ty) then
                   Hashtbl.replace out_ap nm ()
               | None -> ())
        (lookup idx.apply concl);
      (* 지역 가설은 몇 개 없으니 그냥 다 시험한다 *)
      List.iter (fun (id, ty) ->
          if unifies_upto env sigma concl ty then
            Hashtbl.replace out_ap (Id.to_string id) ()) hyps;

      let _t_ap1 = Unix.gettimeofday () in
      (* ── ② apply … in H : 첫 전제 판별트리를 **명제 가설**로 조회 ── *)
      let prop_hyps = List.filter (fun (_, ty) -> is_prop env sigma ty) hyps in
      List.iter
        (fun (_, hty) ->
           List.iter
             (fun (i, d) ->
                if i >= 0 && i < Array.length idx.cands then
                  let c = idx.cands.(i) in
                  let nm = cand_name c in
                  if not (Hashtbl.mem out_in nm) then
                    match cand_type_i env sigma i c with
                    | Some (sg, ty) ->
                      (match descend env sg ty d with
                       | Some (sg, t) ->
                         let hit sg side =
                           Hashtbl.replace out_in nm ();
                           let apre = preorder_of sg side in
                           Hashtbl.replace sig_in nm
                             (rigidity apre, lcp apre (preorder_of sg hty),
                              lgg_size sg side hty) in
                         (match EConstr.kind sg t with
                          | Constr.Prod (_, a, _) ->
                            if unify_ap env sg a hty then hit sg a
                          | _ ->
                            (* ★ iff 결론 — H 가 어느 변과 맞아도 apply-in 이 된다 *)
                            (match iff_sides sg t with
                             | Some (la, ra) ->
                               if unify_ap env sg la hty then hit sg la
                               else if unify_ap env sg ra hty then hit sg ra
                             | None -> ()))
                       | None -> ())
                    | None -> ())
             (lookup idx.prem hty))
        prop_hyps;

      let _t_in1 = Unix.gettimeofday () in
      (* ── ③ rewrite : 결론 **과 모든 가설**의 닫힌 부분항을 redex 로 ── *)
      let subs = ref [] in
      (* ★ redex 가 **어느 가설**에서 왔는지 기록한다.
         예전엔 `DNRWH` 도 `g=goal크기` 를 내보내서, 파이썬의 `('z', z/g)`
         특징이 **가설 redex 를 goal 크기로 정규화**했다 — 무의미하다.
         그리고 "어느 가설인가" 자체가 신호다: 증명은 대개 **방금 만든
         가설**을 재작성한다. 위치를 끝에서부터 센다. *)
      let hyp_info : (Constr.t, int * int) Hashtbl.t = Hashtbl.create 97 in
      let rec go t = subs := t :: !subs; EConstr.iter sigma go t in
      go concl;
      let nh = List.length hyps in
      List.iteri (fun i (_, ty) ->
          let hz = term_size sigma ty in
          let pos = nh - i in            (* 끝에서부터 1,2,3… *)
          let rec mk t =
            let c = EConstr.Unsafe.to_constr t in
            if not (Hashtbl.mem hyp_info c) then Hashtbl.replace hyp_info c (hz, pos);
            EConstr.iter sigma mk t in
          mk ty; go ty) hyps;
      (* ★ redex 고르기 — 세 조건.
         ① 머리가 **경직**(Const/Ind/Construct/Var). Rel·Evar·Sort 는 뺀다.
         ② 닫힌 항만. 바인더 아래 de Bruijn 을 물고 나오면 바깥에서 뜻이 없다.
         ③ **중복 제거.**

         예전 판은 `인자 > 0` 도 걸었는데 그건 버그였다 — 인자 없는 상수도
         정당한 redex 다(`rewrite zwordsize_eq` 의 대상은 `zwordsize` 하나).
         원자를 빼려던 의도였지만 그건 인자 개수가 아니라 **머리 종류**의 문제다. *)
      (* ★ redex 가 **goal 안**인지 가설 안인지 구분한다.
         goal 의 redex 가 훨씬 잘 쓰인다 — `rewrite L` 이 기본이고
         `rewrite L in H` 는 실측 3.8% 뿐이다. *)
      let goal_sub = CH.create 97 in
      let rec mark t =
        CH.replace goal_sub (EConstr.Unsafe.to_constr t) ();
        EConstr.iter sigma mark t in
      mark concl;
      let seenr = CH.create 97 in
      let redexes =
        List.filter
          (fun t ->
             key_of sigma t
             && EConstr.Vars.closed0 sigma t
             && (let c = EConstr.Unsafe.to_constr t in
                 if CH.mem seenr c then false else (CH.add seenr c (); true)))
          !subs in
      (* ★ keyed matching (Coq 8.5+) — `rewrite` 는 redex 의 **머리가 delta 없이**
         맞아야 한다. 우리 `w_unify` 는 delta 를 허용하므로 머리를 따로 확인한다.
         실측 거짓 양성 28.7% 의 자리다. *)
      (* ★ 세 조건을 다 봐야 실제 `rewrite` 와 같아진다.
         ① keyed  — 머리가 delta 없이 맞나 (Coq 8.5+ keyed matching)
         ② unify  — 커널 단일화
         ③ abstract — redex 를 **추상화한 결과가 타입이 맞나**
                      (의존 자리면 rewrite 가 실패한다 — 거짓양성 35.8%) *)
      let concl0 = Proofview.Goal.concl gl in
      (* ★ abstract_ok 메모 — 인자가 (concl0, st) 뿐이라 후보마다 같다.
         예전엔 성공 경로마다 재계산: retyping ~550회/goal ≈ 55ms.
         redex 는 goal 당 ≤~80개 → 그만큼만 계산한다. *)
      let abs_memo : (Constr.t, bool) Hashtbl.t = Hashtbl.create 97 in
      let abstract_ok_m sg st =
        let k = EConstr.Unsafe.to_constr st in
        match Hashtbl.find_opt abs_memo k with
        | Some v -> v
        | None ->
          let v = abstract_ok env sg concl0 st in
          Hashtbl.replace abs_memo k v; v in
      let keyed sg d st =
        same_head sg d st && unify1 env sg d st
        && (not !type_check_rw || abstract_ok_m sg st) in
      let side_matches sg d = List.exists (fun st -> keyed sg d st) redexes in

      (* ★ (후보 i, 깊이 tag/2) → (sg, 변 목록) 캐시.
         descend(evar 사슬 생성) + rw_sides_all(δ·whd 포함)은 **redex 와
         무관**한데 redex 마다 재계산했다 — redex ~80개 × 항목이면 80배 중복. *)
      let sides_memo : (int * int, (Evd.evar_map * (EConstr.t * EConstr.t) list) option)
          Hashtbl.t = Hashtbl.create 257 in
      let sides_of i c tag =
        let key = (i, tag / 2) in
        match Hashtbl.find_opt sides_memo key with
        | Some v -> v
        | None ->
          let v =
            match cand_type_i env sigma i c with
            | None -> None
            | Some (sg, ty) ->
              (match descend env sg ty (tag / 2) with
               | None -> None
               | Some (sg, t) ->
                 let (sg, prs) = rw_sides_all env sg t in
                 if prs = [] then None else Some (sg, prs)) in
          Hashtbl.replace sides_memo key v; v in

      List.iter
        (fun st ->
           List.iter
             (fun (i, tag) ->
                if i >= 0 && i < Array.length idx.cands then
                  let c = idx.cands.(i) in
                  let nm = cand_name c in
                  (* ★ 두 채널은 **배타가 아니다.** 같은 lemma 가
                     `rewrite L` 로도 `rewrite L in H` 로도 될 수 있다.
                     예전엔 `out_rw` 에 들어가면 건너뛰어 `rwh` 를 못 채웠다 —
                     실측(VAL) `rewrite-in` gold 7건 중 2건이 그래서 샜다
                     (합집합 회수 100% vs 자기채널 71.4%).
                     둘 다 찬 뒤에만 건너뛴다. *)
                  if not (Hashtbl.mem out_rw nm && Hashtbl.mem out_rwh nm) then begin
                    assert (tag >= 0);
                    (match sides_of i c tag with
                       | Some (sg, prs) ->
                         (* ★ 묶음 규칙(튜플)이면 성분이 여럿이다. 태그에는
                            성분 번호가 없으므로 **성분을 다 훑는다**.
                            성분이 하나면 태그가 가리키는 변만 본다(빠른 길). *)
                         let cands =
                           match prs with
                           | [(l, r)] -> [if tag mod 2 = 0 then l else r]
                           | _ -> List.concat_map (fun (l, r) -> [l; r]) prs in
                         List.iter (fun d ->
                            let _ing = CH.mem goal_sub (EConstr.Unsafe.to_constr st) in
                            if not (Hashtbl.mem (if _ing then out_rw else out_rwh) nm)
                               && same_head sg d st && unify1 env sg d st
                               && (not !type_check_rw || abstract_ok_m sg st)
                            then begin
                              (if CH.mem goal_sub (EConstr.Unsafe.to_constr st)
                               then Hashtbl.replace out_rw nm ()
                               else Hashtbl.replace out_rwh nm ());
                              (* z = redex 크기, d = 매칭 깊이 *)
                              let dsz = term_size sg st in
                              let dpre = preorder_of sg d in
                              let drig = rigidity dpre in
                              let dl = lcp dpre (preorder_of sg st) in
                              let ing =
                                if CH.mem goal_sub (EConstr.Unsafe.to_constr st)
                                then 1 else 0 in
                              if ing = 1 then begin
                                let prev = match Hashtbl.find_opt sig_rw nm with
                                  | Some (z, dd, l, c, gflag, rg) ->
                                    (max z dsz, dd, max l dl, c + 1, max gflag ing,
                                     max rg drig)
                                  | None -> (dsz, tag / 2, dl, 1, ing, drig) in
                                Hashtbl.replace sig_rw nm prev
                              end else begin
                                let (hz, hp) =
                                  match Hashtbl.find_opt hyp_info
                                          (EConstr.Unsafe.to_constr st) with
                                  | Some v -> v | None -> (0, 0) in
                                let prev = match Hashtbl.find_opt sig_rwh nm with
                                  | Some (z, dd, l, c, h1, h2, rg) ->
                                    (max z dsz, dd, max l dl, c + 1, max h1 hz,
                                     (if h2 = 0 then hp else min h2 hp), max rg drig)
                                  | None -> (dsz, tag / 2, dl, 1, hz, hp, drig) in
                                Hashtbl.replace sig_rwh nm prev
                              end
                            end) cands
                       | None -> ())
                  end)
             (lookup idx.rw st))
        redexes;
      (* ★ 지역 가설도 **바인더를 벗기며** 본다 (`IHcases : forall …, a = b`). *)
      List.iter (fun (id, ty) ->
          match dig_sides env sigma ty with
          | Some (sg, l, r) ->
            let ing d = List.exists
                (fun st -> CH.mem goal_sub (EConstr.Unsafe.to_constr st)
                           && keyed sg d st) redexes in
            (* ★ 지역 가설도 마찬가지 — goal 쪽/가설 쪽을 **따로** 판정한다 *)
            if side_matches sg l || side_matches sg r then begin
              if ing l || ing r then Hashtbl.replace out_rw (Id.to_string id) ();
              (* 가설 redex 로도 되나 — goal 쪽 성공과 무관하게 본다 *)
              let ingh d =
                List.exists (fun st ->
                    not (CH.mem goal_sub (EConstr.Unsafe.to_constr st))
                    && keyed sg d st) redexes in
              if ingh l || ingh r then Hashtbl.replace out_rwh (Id.to_string id) ()
            end
          | None -> ()) hyps;

      let dt = Unix.gettimeofday () -. t0 in
      (* ★ unfold · destruct 채널 — goal 에서 곧바로 결정된다 *)
      let terms = concl :: List.map snd hyps in
      let out_uf = if not !wide_channels then [] else List.map (fun c ->
          Libnames.string_of_qualid
            (Nametab.shortest_qualid_of_global Id.Set.empty (GlobRef.ConstRef c)))
          (try unfold_cands env sigma terms with e when CErrors.noncritical e -> []) in
      let out_ds = if not !wide_channels then [] else List.map (fun i ->
          Libnames.string_of_qualid
            (Nametab.shortest_qualid_of_global Id.Set.empty (GlobRef.IndRef i)))
          (try destruct_cands env sigma terms with e when CErrors.noncritical e -> []) in
      (* ★ dc·uf 채널에도 신호를 붙인다. 예전 판은 `ap`·`rw` 에만 붙여서
         `destruct` 후보 833개가 **무신호**였다 — 나이브 베이즈가 채널 이름
         하나로만 판단해야 했고, 그래서 @10 이 52% 에 머물렀다.
           dc : 결론 인자와 goal 사이의 lgg·lcp (가장 좋은 인자 기준)
           uf : 그 상수가 goal 에 몇 번, 얼마나 크게 나타나나 *)
      let gpre2 = preorder_of sigma concl in
      let sig_dc : (string, int * int) Hashtbl.t = Hashtbl.create 97 in
      let dc_raw = if not !wide_channels then [] else
                   (try decide_cands env sigma terms
                    with e when CErrors.noncritical e -> []) in
      let out_dc = List.map (fun c ->
          let nm = Libnames.string_of_qualid
              (Nametab.shortest_qualid_of_global Id.Set.empty (GlobRef.ConstRef c)) in
          (try
             let (sg, tm) = Evd.fresh_global env sigma (GlobRef.ConstRef c) in
             let ty = Retyping.get_type_of env sg tm in
             let rec concl_of n t =
               if n > max_arrows () then t
               else match EConstr.kind sg t with
                 | Constr.Prod (_, _, b2) -> concl_of (n + 1) b2
                 | Constr.LetIn (_, _, _, b2) -> concl_of (n + 1) b2
                 | Constr.Cast (x, _, _) -> concl_of n x
                 | _ -> t in
             let cc = concl_of 0 ty in
             let (_, args) = EConstr.decompose_app sg cc in
             let bl = ref 0 and bg = ref 0 in
             Array.iter (fun x ->
                 let l = lcp gpre2 (preorder_of sg x) in
                 let g2 = lgg_size sg concl x in
                 if l > !bl then bl := l;
                 if g2 > !bg then bg := g2) args;
             Hashtbl.replace sig_dc nm (!bg, !bl)
           with e when CErrors.noncritical e -> ());
          nm) dc_raw in
      (* uf : goal 안 등장 횟수·크기 *)
      let sig_uf : (string, int * int) Hashtbl.t = Hashtbl.create 31 in
      List.iter (fun nm ->
          let cnt = ref 0 and big = ref 0 in
          let rec go t =
            (match EConstr.kind sigma (fst (EConstr.decompose_app sigma t)) with
             | Constr.Const (c2, _) ->
               let q = Libnames.string_of_qualid
                   (Nametab.shortest_qualid_of_global Id.Set.empty (GlobRef.ConstRef c2)) in
               if q = nm then begin
                 incr cnt;
                 let z = term_size sigma t in if z > !big then big := z
               end
             | _ -> ());
            EConstr.iter sigma go t in
          List.iter go terms;
          Hashtbl.replace sig_uf nm (!cnt, !big)) out_uf;
      (* ★ 채널 사후조건 — 배선이 조용히 어긋나는 것을 막는다.
         `rw`/`rwh` 는 **배타가 아니다** (같은 lemma 가 둘 다 될 수 있다).
         예전엔 배타라서 `rewrite-in` gold 이 샜다. 여기서 그걸 못 박는다. *)
      assert (!raw >= 0 && !keypass >= 0);
      assert (!keypass <= Array.length idx.cands);
      assert (Hashtbl.length out_ap <= Array.length idx.cands);
      assert (Hashtbl.length out_rw <= Array.length idx.cands);
      assert (Hashtbl.length out_rwh <= Array.length idx.cands);
      let _t_rw1 = Unix.gettimeofday () in
      tap_dbg := _t_ap1 -. _t_ap0;
      tin_dbg := _t_in1 -. _t_ap1;
      trw_dbg := _t_rw1 -. _t_in1;
      (env, sigma, out_ap, out_in, out_rw, redexes, hyps, !raw, !keypass, dt,
       sig_ap, sig_rw, term_size sigma concl, out_uf, out_ds, out_dc,
       sig_uf, sig_dc, out_rwh, sig_rwh, sig_in)

let filter_tac () : unit Proofview.tactic =
  Proofview.Goal.enter (fun gl ->
      let (env, sigma, out_ap, out_in, out_rw, redexes, prop_hyps, raw, keypass, dt,
           sig_ap, sig_rw, gsize, out_uf, out_ds, out_dc,
           sig_uf, sig_dc, out_rwh, sig_rwh, sig_in) = compute gl in
      (* 진술문까지 찍으면 랭킹(tf-idf)에 바로 넣을 수 있다. *)
      let flat p =
        let s = Pp.string_of_ppcmds p in
        String.concat " " (String.split_on_char '\n' s) in
      let stmt nm =
        if not !print_types then ""
        else
          try
            let q = Libnames.qualid_of_string nm in
            let g = Smartlocate.global_with_alias q in
            let (sg, tm) = Evd.fresh_global env sigma g in
            let ty = Retyping.get_type_of env sg tm in
            " :: " ^ flat (Printer.pr_econstr_env env sg ty)
          with e when CErrors.noncritical e -> "" in
      let sg_of h n = match Hashtbl.find_opt h n with
        | Some (a, b, c, d) -> Printf.sprintf " lgg=%d e=%d lcp=%d rig=%d" a b c d
        | None -> "" in
      Hashtbl.iter (fun n () ->
          Feedback.msg_notice
            (str "APPLIC " ++ str n ++ str (sg_of sig_ap n)
             ++ str (Printf.sprintf " g=%d" gsize) ++ str (stmt n))) out_ap;
      Hashtbl.iter (fun n () ->
          Feedback.msg_notice
            (str "APPLICIN " ++ str n
             ++ str (match Hashtbl.find_opt sig_in n with
                 | Some (rg, l, g2) ->
                   Printf.sprintf " rig=%d lcp=%d lgg=%d" rg l g2
                 | None -> "")
             ++ str (stmt n))) out_in;
      Hashtbl.iter (fun n () ->
          Feedback.msg_notice
            (str "DNRW " ++ str n
             ++ str (match Hashtbl.find_opt sig_rw n with
                 | Some (z, d, l, c, gflag, rg) ->
                   Printf.sprintf " z=%d d=%d lcp=%d nm=%d ing=%d rig=%d"
                     z d l c gflag rg
                 | None -> "")
             ++ str (Printf.sprintf " g=%d" gsize) ++ str (stmt n))) out_rw;
      Hashtbl.iter (fun n () ->
          Feedback.msg_notice
            (str "DNRWH " ++ str n
             ++ str (match Hashtbl.find_opt sig_rwh n with
                 | Some (z, d, l, c, hz, hp, rg) ->
                   (* ★ `g` 는 **그 가설의 크기**다 (goal 크기가 아니다).
                      `hp` = 끝에서부터의 가설 위치 — 1이 가장 최근이다. *)
                   Printf.sprintf " z=%d d=%d lcp=%d nm=%d ing=0 hp=%d rig=%d"
                     z d l c hp rg
                 | None -> "")
             ++ str (Printf.sprintf " g=%d"
                       (match Hashtbl.find_opt sig_rwh n with
                        | Some (_, _, _, _, hz, _, _) when hz > 0 -> hz
                        | _ -> gsize))
             ++ str (stmt n))) out_rwh;
      List.iter (fun n ->
          Feedback.msg_notice
            (str "UNFOLD " ++ str n
             ++ str (match Hashtbl.find_opt sig_uf n with
                 | Some (c, z) -> Printf.sprintf " occ=%d z=%d" c z
                 | None -> "")
             ++ str (Printf.sprintf " g=%d" gsize) ++ str (stmt n))) out_uf;
      List.iter (fun n -> Feedback.msg_notice (str "DESTRUCT " ++ str n)) out_ds;
      List.iter (fun n ->
          Feedback.msg_notice
            (str "DECIDE " ++ str n
             ++ str (match Hashtbl.find_opt sig_dc n with
                 | Some (g2, l) -> Printf.sprintf " lgg=%d lcp=%d" g2 l
                 | None -> "")
             ++ str (Printf.sprintf " g=%d" gsize) ++ str (stmt n))) out_dc;
      (* ★ 지역 가설 이름 — 이걸 알아야 `destruct l` 을 "검색 미적중" 으로
         잘못 세지 않는다. 지역 변수는 애초에 검색 대상이 아니다. *)
      Feedback.msg_notice
        (str "HYPS " ++ str (String.concat " "
           (List.map (fun (id, _) -> Id.to_string id) prop_hyps)));
      (* ★ goal 의 **바인더 이름**도 낸다. `induction l; simpl; intros.` 처럼
         `intros` 가 뒤에 오면 `l` 은 가설이 아니라 아직 goal 의 바인더다.
         가설 목록만 보면 "검색 미적중" 으로 잘못 세게 된다(실측 induction 21건). *)
      let rec binders acc n t =
        if n > 40 then acc
        else match EConstr.kind sigma t with
          | Constr.Prod (na, _, b2) ->
            let acc = (match na.Context.binder_name with
                | Names.Name.Name i -> Id.to_string i :: acc
                | Names.Name.Anonymous -> acc) in
            binders acc (n + 1) b2
          | Constr.LetIn (na, _, _, b2) ->
            let acc = (match na.Context.binder_name with
                | Names.Name.Name i -> Id.to_string i :: acc
                | Names.Name.Anonymous -> acc) in
            binders acc (n + 1) b2
          | _ -> acc in
      Feedback.msg_notice
        (str "GBIND " ++ str (String.concat " "
           (binders [] 0 (Proofview.Goal.concl gl))));
      Feedback.msg_notice
        (str (Printf.sprintf
                "APPLIC_STAT ver=%s cand=%d pat=%d build=%.3f hyps=%d redex=%d raw=%d \
                 keypass=%d apply=%d applyin=%d rewrite=%d rewriteh=%d unfold=%d destruct=%d decide=%d iffp=%d ifff=%d wca=%d tap=%.3f tin=%.3f trw=%.3f sec=%.4f"
                retrieval_version
                (Array.length idx.cands) idx.npat idx.build (List.length prop_hyps)
                (List.length redexes) raw keypass
                (Hashtbl.length out_ap) (Hashtbl.length out_in)
                (Hashtbl.length out_rw) (Hashtbl.length out_rwh) (List.length out_uf) (List.length out_ds) (List.length out_dc)
                !iffp_dbg !iffp_fail !wca_dbg !tap_dbg !tin_dbg !trw_dbg dt));
      Proofview.tclUNIT ())

(* ★ 진단 — 이름 하나의 **결론 sort** 를 찍는다.
   `Prop` 결론만 색인해도 gold 을 안 놓치는지 확인하려고 만들었다.
   mathcomp 후보 21,512개 중 `Order` 4,216개가 HB 배관이라 큰 절감이 걸려 있다. *)
let sort_tac (g : GlobRef.t) =
  Proofview.Goal.enter (fun gl ->
      let env = Proofview.Goal.env gl in
      let sigma = Proofview.Goal.sigma gl in
      let name =
        Libnames.string_of_qualid (Nametab.shortest_qualid_of_global Id.Set.empty g) in
      (try
         let (sg, tm) = Evd.fresh_global env sigma g in
         let ty = Retyping.get_type_of env sg tm in
         (* 결론까지 Π 를 벗긴다 (evar 없이 — sort 만 보면 된다) *)
         let rec concl n t =
           if n > 40 then t
           else match EConstr.kind sg t with
             | Constr.Prod (_, _, b) -> concl (n + 1) b
             | Constr.LetIn (_, _, _, b) -> concl (n + 1) b
             | Constr.Cast (c, _, _) -> concl n c
             | _ -> t in
         let c = concl 0 ty in
         let so =
           try
             let k = EConstr.ESorts.kind sg (Retyping.get_sort_of env sg c) in
             if Sorts.is_prop k then "Prop"
             else if Sorts.is_set k then "Set" else "Type"
           with e when CErrors.noncritical e -> "?" in
         let hd =
           match EConstr.kind sg (fst (EConstr.decompose_app sg c)) with
           | Constr.Const (cc, _) -> "c:" ^ Constant.to_string cc
           | Constr.Ind (i, _) -> "i:" ^ MutInd.to_string (fst i)
           | Constr.Construct _ -> "k" | Constr.Var _ -> "v"
           | Constr.Prod _ -> "Prod" | Constr.Sort _ -> "Sort" | _ -> "?" in
         Feedback.msg_notice
           (Pp.str (Printf.sprintf "SORT %s %s %s" name so hd))
       with e when CErrors.noncritical e ->
         Feedback.msg_notice (Pp.str (Printf.sprintf "SORT %s ? ?" name)));
      Proofview.tclUNIT ())

let set_prop_only b = prop_only := b; idx.nglob <- -1
let set_delta b = delta_unfold := b; Hashtbl.reset delta_ok; idx.nglob <- -1
let set_wide b = wide_channels := b
let set_depth n =
  assert (n >= 1 && n <= 32);        (* 0 이면 트리가 아무것도 안 가른다 *)
  dn_depth := n; idx.nglob <- -1
let set_setoid b = use_setoid := b; idx.nglob <- -1
let set_rigid b = rigid_mode := b; idx.nglob <- -1
let set_exact b = exact_depth := b
let set_apply_dn b = apply_dn := b
let set_type_check_rw b = type_check_rw := b
let set_arrows n =
  assert (n >= 0 && n <= 64);        (* 음수면 색인이 통째로 빈다 *)
  max_arrows_r := (if n < 1 then 1 else n); idx.nglob <- -1
let set_print_types b = print_types := b

let canon (r : Libnames.qualid) =
  (* ★ `Nametab.locate` 는 **축약(Notation … := …)** 을 못 찾는다.
     `sym_eq` · `Zmult_1_r` · `Zplus_le_0_compat` 이 그런 별칭이라
     정답 이름이 `?` 로 나오고 **가짜 미검출**이 됐다(놓친 11 중 3).
     `Smartlocate.global_with_alias` 는 별칭까지 푼다. *)
  let nm =
    try
      let g = Smartlocate.global_with_alias r in
      Libnames.string_of_qualid (Nametab.shortest_qualid_of_global Id.Set.empty g)
    with e when CErrors.noncritical e ->
      (try
         let g = Nametab.locate r in
         Libnames.string_of_qualid (Nametab.shortest_qualid_of_global Id.Set.empty g)
       with Not_found -> "?") in
  Feedback.msg_notice
    (str "CANON " ++ str (Libnames.string_of_qualid r) ++ str " -> " ++ str nm)


(* ── 진단: 정답이 왜 안 나왔나 ──────────────────────────────────────────
 * 정답 lemma 를 직접 받아서
 *   · 실제로 몇 번째 화살표에서 goal 과 맞는지(깊이)
 *   · 그 결론의 **머리 기호**와 goal 의 머리 기호
 *   · 판별트리(apply/rw)가 그 후보를 돌려주는지
 * 를 찍는다. 머리가 다르면 그 둘 중 하나가 **펼쳐져야 하는 상수**다. *)

let head_str env sigma t =
  match EConstr.kind sigma (fst (EConstr.decompose_app sigma t)) with
  | Constr.Const (c, _) -> "C:" ^ Constant.to_string c
  | Constr.Ind (i, _) -> "I:" ^ MutInd.to_string (fst i)
  | Constr.Construct (((mi, i), j), _) ->
    "K:" ^ MutInd.to_string mi ^ "/" ^ string_of_int i ^ "/" ^ string_of_int j
  | Constr.Var v -> "V:" ^ Id.to_string v
  | Constr.Sort _ -> "S"
  | Constr.Evar _ -> "?"
  | Constr.Rel _ -> "R"
  | _ -> "-"

(* tactic 인자의 `reference` 는 이미 해석된 `GlobRef.t` 로 온다 (vernac 은 qualid). *)
(* ★ 처음 어긋나는 자리를 찾는다. 판별트리는 깊이 2 까지 라벨로 가르므로
   머리만 비교하면 안 된다 — 인자 자리에서 갈리는 경우가 대부분이다. *)
let rec first_diff env sigma d a b =
  if d > 3 then None
  else
    let (ha, aa) = EConstr.decompose_app sigma a in
    let (hb, ab) = EConstr.decompose_app sigma b in
    let flex t = match EConstr.kind sigma t with
      | Constr.Evar _ | Constr.Rel _ | Constr.Meta _ -> true | _ -> false in
    if flex ha || flex hb then None
    else if head_str env sigma a <> head_str env sigma b then
      Some (head_str env sigma a, head_str env sigma b)
    else
      let n = min (Array.length aa) (Array.length ab) in
      let rec go i =
        if i >= n then None
        else match first_diff env sigma (d + 1) aa.(i) ab.(i) with
          | Some r -> Some r
          | None -> go (i + 1)
      in go 0

let why_tac (g : GlobRef.t) : unit Proofview.tactic =
  Proofview.Goal.enter (fun gl ->
      let env = Proofview.Goal.env gl in
      let sigma = Proofview.Goal.sigma gl in
      let concl = Proofview.Goal.concl gl in
      if idx.nglob <> nb_globals env then build_index env sigma;
      let name = Libnames.string_of_qualid
          (Nametab.shortest_qualid_of_global Id.Set.empty g) in
      let inlist dn t =
        List.exists
          (fun (i, _) -> i >= 0 && i < Array.length idx.cands
                         && cand_name idx.cands.(i) = name)
          (try DN.lookup env sigma (ts ()) dn t
           with e when CErrors.noncritical e -> []) in
      let (sg, tm) = Evd.fresh_global env sigma g in
      let ty = Retyping.get_type_of env sg tm in
      (* apply 로 맞는 깊이 *)
      let rec find d =
        if d > max_arrows () then None
        else match descend env sg ty d with
          | Some (s2, t) when unify1 env s2 t concl -> Some (d, s2, t)
          | _ -> find (d + 1) in
      (* redex 목록 (rewrite 판정용) *)
      let hyps = local_hyps env in
      let subs = ref [] in
      let rec walk t = subs := t :: !subs; EConstr.iter sigma walk t in
      walk concl; List.iter (fun (_, ty) -> walk ty) hyps;
      let redexes = List.filter
          (fun t -> rigid_head sigma t
                    && Array.length (snd (EConstr.decompose_app sigma t)) > 0
                    && EConstr.Vars.closed0 sigma t) !subs in
      let dn_a = inlist idx.apply concl in
      let dn_p = List.exists (fun (_, h) -> inlist idx.prem h) hyps in
      let dn_r = List.exists (fun st -> inlist idx.rw st) redexes in
      (match find 0 with
       | Some (d, s2, t) ->
         let diff = match first_diff env s2 0 t concl with
           | Some (x, y) -> x ^ " vs " ^ y | None -> "none" in
         Feedback.msg_notice
           (str (Printf.sprintf
                   "WHY %s ok depth=%d dnA=%d dnP=%d dnR=%d diff=%s"
                   name d (if dn_a then 1 else 0) (if dn_p then 1 else 0)
                   (if dn_r then 1 else 0) diff))
       | None ->
         Feedback.msg_notice
           (str (Printf.sprintf "WHY %s noapply dnA=%d dnP=%d dnR=%d diff=-"
                   name (if dn_a then 1 else 0) (if dn_p then 1 else 0)
                   (if dn_r then 1 else 0))));
      Proofview.tclUNIT ())

(* ★ 위음성 추정용 — 후보 우주에서 균등 표본을 뽑아 준다.
   필터가 **거부한** 것 중 실제로 되는 게 있는지 재려면 이게 있어야 한다. *)
let sample_tac (n : int) : unit Proofview.tactic =
  Proofview.Goal.enter (fun gl ->
      let env = Proofview.Goal.env gl in
      let sigma = Proofview.Goal.sigma gl in
      if idx.nglob <> nb_globals env then build_index env sigma;
      let n = if n <= 0 then 1 else n in
      Array.iteri
        (fun i c ->
           if i mod n = 0 then
             Feedback.msg_notice (str "SAMPLE " ++ str (cand_name c)))
        idx.cands;
      Proofview.tclUNIT ())

let transparent_of (r : Libnames.qualid) =
  match (try Some (Smartlocate.global_with_alias r)
         with e when CErrors.noncritical e -> None) with
  | Some (GlobRef.ConstRef c) -> add_transparent c; idx.nglob <- -1
  | _ -> ()


(* ── ★ 정답이 **실제 파이프라인**에서 살아남나 ────────────────────────────
 * 예전 진단(`applic_why`)은 `apply` 를 판별트리로 쟀는데 apply 는 **선형 훑기**를
 * 쓴다 — 측정 자체가 파이프라인과 달랐다. 그리고 지역 가설은 색인에 없어서
 * 무조건 미검출로 잡혔다(`P`·`IHcases`).
 * 여기서는 `applic_filter` 와 **같은 함수**를 돌리고 결과를 확인만 한다. *)

let check_tac (g : GlobRef.t) : unit Proofview.tactic =
  Proofview.Goal.enter (fun gl ->
      let (env, sigma, out_ap, out_in, out_rw, redexes, _hyps, raw, keypass, dt,
           _sa, _sr, _gs, _uf, _ds, _dc, _su, _sd, _rwh, _srwh, _sin) = compute gl in
      let name =
        Libnames.string_of_qualid (Nametab.shortest_qualid_of_global Id.Set.empty g) in
      let mem h = if Hashtbl.mem h name then 1 else 0 in
      (* 판별트리가 그 후보를 돌려주기는 하나 (귀속용) *)
      let inlist dn t =
        List.exists
          (fun (i, _) -> i >= 0 && i < Array.length idx.cands
                         && cand_name idx.cands.(i) = name)
          (try DN.lookup env sigma (ts ()) dn t
           with e when CErrors.noncritical e -> []) in
      let dnr = List.exists (fun st -> inlist idx.rw st) redexes in
      (* rewrite 사슬을 단계별로 — 어디서 끊기는지 *)
      let (sdepth, headm, unifm) =
        match (try Some (Evd.fresh_global env sigma g) with _ -> None) with
        | None -> (-1, 0, 0)
        | Some (sg0, tm) ->
          (try
             let ty = Retyping.get_type_of env sg0 tm in
             match dig_sides env sg0 ty with
             | None -> (-1, 0, 0)
             | Some (sg, l, r) ->
               let hm = List.exists (fun st -> same_head sg l st || same_head sg r st)
                   redexes in
               let um = List.exists
                   (fun st -> (same_head sg l st && unify1 env sg l st)
                              || (same_head sg r st && unify1 env sg r st)) redexes in
               (0, (if hm then 1 else 0), (if um then 1 else 0))
           with e when CErrors.noncritical e -> (-1, 0, 0))
      in
      let concl = Proofview.Goal.concl gl in
      let dna = inlist idx.apply concl in
      (* 색인에 아예 없는가 (지역 가설이면 정상) *)
      let indexed =
        Array.exists (fun c -> cand_name c = name) idx.cands in
      (* ★ 지역 이름을 **여기서도** 낸다. `filter_tac` 에만 있어서
         `applic_check` 를 쓰는 다중프로젝트 측정이 `destruct l` 의 `l` 을
         전부 "미검출" 로 셌다(VAL 58.6% 의 상당 부분이 이것이었다). *)
      Feedback.msg_notice
        (str "HYPS " ++ str (String.concat " "
           (List.map (fun (id, _) -> Id.to_string id) (local_hyps env))));
      let rec binders acc n t =
        if n > 40 then acc
        else match EConstr.kind sigma t with
          | Constr.Prod (na, _, b2) | Constr.LetIn (na, _, _, b2) ->
            let acc = (match na.Context.binder_name with
                | Names.Name.Name i -> Id.to_string i :: acc
                | Names.Name.Anonymous -> acc) in
            binders acc (n + 1) b2
          | _ -> acc in
      Feedback.msg_notice
        (str "GBIND " ++ str (String.concat " " (binders [] 0 concl)));
      Feedback.msg_notice
        (str (Printf.sprintf
                "CHECK ver=%s %s ap=%d in=%d rw=%d dnA=%d dnR=%d indexed=%d sides=%d headm=%d unifm=%d nap=%d nin=%d nrw=%d redex=%d raw=%d keypass=%d sec=%.3f"
                retrieval_version
                name (mem out_ap) (mem out_in) (mem out_rw)
                (if dna then 1 else 0) (if dnr then 1 else 0)
                (if indexed then 1 else 0) sdepth headm unifm
                (Hashtbl.length out_ap) (Hashtbl.length out_in)
                (Hashtbl.length out_rw) (List.length redexes) raw keypass dt));
      Proofview.tclUNIT ())
