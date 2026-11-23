#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <cstdio>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "gauge_coexistence.h"

static const char production[]="/var/opt/hmi/data/ID5/Plugins/HudTest/hud-enabled";
static const char* preference;
static unsigned launches;
// The current menu is session-only. A legacy preference must never auto-arm it.
struct PreferenceIO {
    static unsigned accesses,creates,renames;
    static FILE* open(const char* path,const char* mode) {
        if (!strcmp(path,production)) { ++accesses;path=preference; }
        return fopen(path,mode);
    }
    static int temporary(char* path) {
        ++creates;
        assert(!strcmp(path,"/var/opt/hmi/data/ID5/Plugins/HudTest/hud-enabled.XXXXXX"));
        strcpy(path,"/tmp/id6-hud-setting-XXXXXX");return mkstemp(path);
    }
    static int move(const char* from,const char* to) {
        ++renames;assert(!strcmp(to,production));return rename(from,preference);
    }
};
unsigned PreferenceIO::accesses=0,PreferenceIO::creates=0,PreferenceIO::renames=0;
#define DIAGNOSTIC_WORKER_H
static inline pid_t launch(const char*const*,int) { ++launches;return -1; }
#define fopen PreferenceIO::open
#define mkstemp PreferenceIO::temporary
#define rename PreferenceIO::move
#include "../src/plugins/hud_menu.cpp"
#undef rename
#undef mkstemp
#undef fopen

static void seed() {
    FILE* file=fopen(preference,"wb"); assert(file); assert(fwrite("1\n",1,2,file)==2);assert(!fclose(file));
}
static void persisted() {
    FILE* file=fopen(preference,"rb"); assert(file);assert(fgetc(file)=='1' && fgetc(file)=='\n' && fgetc(file)==EOF);fclose(file);
}
static void untouched_preference() {
    persisted();
    assert(!PreferenceIO::accesses && !PreferenceIO::creates && !PreferenceIO::renames);
}
static void blocked() {
    bmw::IDispatcher dispatcher;bmw::Bundle bundle;bmw::RHMIInterfaceVersion version={1};
    HudTest app(dispatcher,bmw::BasicString<char>("HudTest"),1,0,version,bundle,bundle);
    assert(app.onInit());
    assert(!app.bools[51] && !app.posts && !launches);untouched_preference();
    app.testAction(21);
    assert(!app.bools[51] && !app.posts && !launches && app.texts[50].find("HUD")!=std::string::npos);
    bmw::Parcel empty;
    for(unsigned i=0;i<5;++i) assert(app.invokeDataUpdate(0x48554454u,empty));
    assert(!launches && !app.posts);untouched_preference();
    app.testAction(21);assert(!app.bools[51] && !launches);untouched_preference();
}
int main() {
    char path[]="/tmp/id6-hud-pref-XXXXXX";int fd=mkstemp(path);assert(fd>=0);close(fd);preference=path;seed();
    unsetenv("ID6_FAKE_AAD_INSTALLED");unsetenv("ID6_FAKE_CARPLAY_HUD");unsetenv("ID6_FAKE_AAD_SHOWN");
    setenv("ID6_FAKE_AAD_INSTALLED","1",1);blocked();unsetenv("ID6_FAKE_AAD_INSTALLED");
    setenv("ID6_FAKE_CARPLAY_HUD","1",1);blocked();unsetenv("ID6_FAKE_CARPLAY_HUD");
    setenv("ID6_FAKE_AAD_SHOWN","1",1);blocked();unsetenv("ID6_FAKE_AAD_SHOWN");
    const unsigned ports[]={BOOST_MOST_PORT,SHIFT_MOST_PORT,LAUNCH_MOST_PORT,POWER_MOST_PORT,BASE_MOST_PORT,WARM_MOST_PORT};
    for(unsigned i=0;i<sizeof ports/sizeof ports[0];++i) {
        fd=gauge_bind(ports[i]);assert(fd>=0);blocked();close(fd);
    }
    { bmw::IDispatcher dispatcher; bmw::Bundle bundle; bmw::RHMIInterfaceVersion version={1};
      HudTest app(dispatcher,bmw::BasicString<char>("HudTest"),1,0,version,bundle,bundle);
      assert(app.onInit());assert(!app.bools[51] && !launches && !app.posts);untouched_preference();
      app.testAction(21);assert(app.bools[51] && launches==1 && app.posts==1);untouched_preference();
      app.testAction(21);assert(!app.bools[51]);
      bmw::Parcel empty;
      for(unsigned i=0;i<5;++i) assert(app.invokeDataUpdate(0x48554454u,empty));
      assert(launches==1);untouched_preference(); }
    unlink(path);
    puts("HUD menu: actual class projection/MOST veto, no spawn loop, legacy preference untouched, explicit session toggle and unobstructed launch OK");
}
