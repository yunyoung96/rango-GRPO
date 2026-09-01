applic_plugin_MLPACK_DEPENDENCIES:=applic_main applic
applic_main.cmx : FOR_PACK=-for-pack Applic_plugin
applic.cmx : FOR_PACK=-for-pack Applic_plugin
applic_plugin.cmo:$(addsuffix .cmo,$(applic_plugin_MLPACK_DEPENDENCIES))
applic_plugin.cmx:$(addsuffix .cmx,$(applic_plugin_MLPACK_DEPENDENCIES))
