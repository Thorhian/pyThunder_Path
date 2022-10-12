#include <renderdoc_app.h>
#include <iostream>
#include <assert.h>

#if !defined (WIN32) || !defined (_WIN32) || !defined (__WIN32) && defined (__CYGWIN__)
#include <dlfcn.h>
#endif


//API must be connected to dynamically. Will return the pointer to API stuff.
RENDERDOC_API_1_1_2 *checkGetAPI() {
   RENDERDOC_API_1_1_2 *rdoc_api = NULL;

#if defined (WIN32) || defined (_WIN32) || defined (__WIN32) && !defined (__CYGWIN__)
   std::cout << "Windows renderdoc debugging is currently not supported.\n";
   return NULL;
#else
   if(void *mod = dlopen("librenderdoc.so", RTLD_NOW | RTLD_NOLOAD)) {
      pRENDERDOC_GetAPI RENDERDOC_GetAPI;
      RENDERDOC_GetAPI = (pRENDERDOC_GetAPI)dlsym(mod, "RENDERDOC_GetAPI");
      int ret = RENDERDOC_GetAPI(eRENDERDOC_API_Version_1_1_2, (void **)&rdoc_api);
      assert(ret == 1);
   }
#endif

return rdoc_api;
}
