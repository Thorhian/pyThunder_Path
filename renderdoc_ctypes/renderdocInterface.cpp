#include <renderdoc_app.h>
#include <iostream>
#include <assert.h>

#if !defined (WIN32) || !defined (_WIN32) || !defined (__WIN32)
#include <dlfcn.h>
#endif

//To avoid C++ name mangling
extern "C" {

//Test/sanity function
void helloWorld() {
   std::cout << "Hello World\n";
}

//API must be connected to dynamically. Will return the pointer to API stuff.
void *checkGetAPI() {
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

void startCapture(RENDERDOC_API_1_1_2 *apiPointer) {
   if(apiPointer) apiPointer->StartFrameCapture(NULL, NULL);
   std::cout << "RenderDoc Capture Started, gaben.\n";
}

void endCapture(RENDERDOC_API_1_1_2 *apiPointer) {
   if(apiPointer) apiPointer->EndFrameCapture(NULL, NULL);
   std::cout << "RenderDoc Capture Finished, gaben.\n";
}
}
