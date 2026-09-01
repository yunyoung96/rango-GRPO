let _ = Mltop.add_known_module "coq-applic.plugin"

# 3 "applic.mlg"
 
open Ltac_plugin
open Stdarg


let () = Tacentries.tactic_extend "coq-applic.plugin" "applic_filter" ~level:0 
         [(Tacentries.TyML (Tacentries.TyIdent ("applic_filter", Tacentries.TyNil), 
           (fun ist -> 
# 9 "applic.mlg"
                           Applic_main.filter_tac () 
           )))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicPropOnly" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicPropOnly", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 13 "applic.mlg"
                                   Applic_main.set_prop_only (n <> 0) 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicDelta" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicDelta", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 17 "applic.mlg"
                                Applic_main.set_delta (n <> 0) 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicWideChannels" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicWideChannels", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 21 "applic.mlg"
                                       Applic_main.set_wide (n <> 0) 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicDepth" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicDepth", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 25 "applic.mlg"
                                Applic_main.set_depth n 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicSetoid" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicSetoid", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 29 "applic.mlg"
                                 Applic_main.set_setoid (n <> 0) 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicCanon" ~classifier:(fun _ -> Vernacextend.classify_as_query) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicCanon", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_reference), 
                                     Vernacextend.TyNil)), (let coqpp_body r
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 33 "applic.mlg"
                                      Applic_main.canon r 
                                                                ) in fun r
                                                           ?loc ~atts ()
                                                           -> coqpp_body r
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicRigid" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicRigid", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 37 "applic.mlg"
                                Applic_main.set_rigid (n <> 0) 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicExact" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicExact", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 41 "applic.mlg"
                                Applic_main.set_exact (n <> 0) 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicApplyDN" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicApplyDN", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 45 "applic.mlg"
                                  Applic_main.set_apply_dn (n <> 0) 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Tacentries.tactic_extend "coq-applic.plugin" "applic_why" ~level:0 
         [(Tacentries.TyML (Tacentries.TyIdent ("applic_why", Tacentries.TyArg (
                                                              Extend.TUentry (Genarg.get_arg_tag wit_reference), 
                                                              Tacentries.TyNil)), 
           (fun r ist -> 
# 49 "applic.mlg"
                                     Applic_main.why_tac r 
           )))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicTransparent" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicTransparent", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_reference), 
                                     Vernacextend.TyNil)), (let coqpp_body r
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 53 "applic.mlg"
                                            Applic_main.transparent_of r 
                                                                ) in fun r
                                                           ?loc ~atts ()
                                                           -> coqpp_body r
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicClearTransparent" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicClearTransparent", 
                                     Vernacextend.TyNil), (let coqpp_body () = 
                                                          Vernacextend.vtdefault (fun () -> 
                                                          
# 57 "applic.mlg"
                                    Applic_main.clear_transparent () 
                                                          ) in fun ?loc ~atts ()
                                                          -> coqpp_body (Attributes.unsupported_attributes atts)), None))]

let () = Tacentries.tactic_extend "coq-applic.plugin" "applic_sort" ~level:0 
         [(Tacentries.TyML (Tacentries.TyIdent ("applic_sort", Tacentries.TyArg (
                                                               Extend.TUentry (Genarg.get_arg_tag wit_reference), 
                                                               Tacentries.TyNil)), 
           (fun r ist -> 
# 61 "applic.mlg"
                                      Applic_main.sort_tac r 
           )))]

let () = Tacentries.tactic_extend "coq-applic.plugin" "applic_sample" ~level:0 
         [(Tacentries.TyML (Tacentries.TyIdent ("applic_sample", Tacentries.TyArg (
                                                                 Extend.TUentry (Genarg.get_arg_tag wit_int_or_var), 
                                                                 Tacentries.TyNil)), 
           (fun n ist -> 
# 65 "applic.mlg"
                                         Applic_main.sample_tac n 
           )))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicPrintTypes" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicPrintTypes", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 69 "applic.mlg"
                                     Applic_main.set_print_types (n <> 0) 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Tacentries.tactic_extend "coq-applic.plugin" "applic_check" ~level:0 
         [(Tacentries.TyML (Tacentries.TyIdent ("applic_check", Tacentries.TyArg (
                                                                Extend.TUentry (Genarg.get_arg_tag wit_reference), 
                                                                Tacentries.TyNil)), 
           (fun r ist -> 
# 73 "applic.mlg"
                                       Applic_main.check_tac r 
           )))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicArrows" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicArrows", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 77 "applic.mlg"
                                 Applic_main.set_arrows n 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

let () = Vernacextend.static_vernac_extend ~plugin:(Some "coq-applic.plugin") ~command:"ApplicTypeCheckRW" ~classifier:(fun _ -> Vernacextend.classify_as_sideeff) ?entry:None 
         [(Vernacextend.TyML (false, Vernacextend.TyTerminal ("ApplicTypeCheckRW", 
                                     Vernacextend.TyNonTerminal (Extend.TUentry (Genarg.get_arg_tag wit_int), 
                                     Vernacextend.TyNil)), (let coqpp_body n
                                                           () = Vernacextend.vtdefault (fun () -> 
                                                                
# 81 "applic.mlg"
                                      Applic_main.set_type_check_rw (n <> 0) 
                                                                ) in fun n
                                                           ?loc ~atts ()
                                                           -> coqpp_body n
                                                           (Attributes.unsupported_attributes atts)), None))]

