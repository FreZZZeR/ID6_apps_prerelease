#include "gauge_preferences.h"
#include "gauge_core.h"
#include "n57.h"
#include <assert.h>
#include <arpa/inet.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>
#include <map>
#include <string>
#include <vector>

static char fixture_dir[128];
static bool fail_assignments,fail_preferences,fail_names;
static unsigned configured_n57=0x010203;
static uint64_t fixture_now=100000;
static std::string storagePath(const char* path) {
    const char* prefix="/var/opt/hmi/data/ID5/";
    return strncmp(path,prefix,strlen(prefix)) ? path : std::string(fixture_dir)+"/"+(path+strlen(prefix));
}
static FILE* fixture_fopen(const char* path,const char* mode) {
    return fopen(storagePath(path).c_str(),mode);
}
static bool fixture_save(const char* path,const unsigned char* bytes,size_t length) {
    if ((fail_assignments && strstr(path,"BoostDeck.signals")) ||
        (fail_preferences && strstr(path,"BoostDeck.prefs")) ||
        (fail_names && strstr(path,"BoostDeck.panels"))) return false;
    return savePersistentBytes(storagePath(path).c_str(),bytes,length);
}
#define fopen fixture_fopen
#define savePersistentBytes fixture_save
#include "boost_preferences.h"
#include "boostdeck_assignments.h"
#undef fopen
#undef savePersistentBytes

struct Child {
    bool exited,stopping,tone;
    Child(bool is_tone):exited(false),stopping(false),tone(is_tone){}
};
static std::map<pid_t,Child> children;
static std::vector<std::vector<std::string> > launches;
static pid_t next_pid=100;
static unsigned collectorLaunches() {
    unsigned n=0;
    for (unsigned i=0;i<launches.size();++i) if (launches[i].size()>1 && launches[i][1]!="--alert-tone") ++n;
    return n;
}
static unsigned activeCollectors() {
    unsigned n=0;
    for (std::map<pid_t,Child>::const_iterator i=children.begin();i!=children.end();++i)
        if (!i->second.tone) ++n;
    return n;
}
static pid_t fixture_launch(const char* const* args,int) {
    std::vector<std::string> copied;
    for (unsigned i=0;args[i];++i) copied.push_back(args[i]);
    const bool tone=copied.size()>1 && copied[1]=="--alert-tone";
    assert(tone || activeCollectors()==0);
    launches.push_back(copied);
    children.insert(std::make_pair(++next_pid,Child(tone)));
    return next_pid;
}
static pid_t fixture_waitpid(pid_t pid,int*,int flags) {
    assert(flags==WNOHANG);
    std::map<pid_t,Child>::iterator child=children.find(pid);
    if (child==children.end()) {errno=ECHILD;return -1;}
    if (!child->second.exited) return 0;
    children.erase(child);return pid;
}
static int fixture_kill(pid_t pid,int signal) {
    assert(signal==SIGTERM && children.count(pid));
    children.find(pid)->second.stopping=true;return 0;
}
static unsigned fixture_n57(const char*) {return configured_n57;}
static uint64_t fixture_clock() {return fixture_now;}
#define DIAGNOSTIC_WORKER_H
#define launch fixture_launch
#define waitpid fixture_waitpid
#define kill fixture_kill
#define n57_index_file fixture_n57
#define bd_mono_ms fixture_clock
#include "../src/plugins/boost_deck.cpp"
#undef launch
#undef waitpid
#undef kill
#undef n57_index_file
#undef bd_mono_ms

static void tick(BoostDeck& app) {app.testDeliver(app.testLastMessage(kPollKey));}
static void finishStopped(BoostDeck& app) {
    for (std::map<pid_t,Child>::iterator i=children.begin();i!=children.end();++i)
        if (i->second.stopping) i->second.exited=true;
    tick(app);
}
static bd_mask launchedMask() {
    for (unsigned i=static_cast<unsigned>(launches.size());i>0;--i) {
        const std::vector<std::string>& args=launches[i-1];
        for (unsigned j=0;j+1<args.size();++j)
            if (args[j]=="--signals") return strtoull(args[j+1].c_str(),0,10);
    }
    assert(false);return 0;
}

int main() {
    char directory[]="/tmp/id6-boost-deck-XXXXXX";assert(mkdtemp(directory));
    strcpy(fixture_dir,directory);
    unsigned char initial[2][kBoostDeckSlots];
    bool diesel,hidden;
    loadBoostDeckAssignments("/nonexistent",initial,diesel,hidden,true);
    initial[1][0]=BD_REL_TORQUE_DDE;initial[1][1]=BD_ADBLUE;
    assert(saveBoostDeckAssignments(kAssignments,initial,true,false));
    BoostPreferences prefs;
    prefs.choice[BOOST_STYLE]=1;prefs.choice[BOOST_PRESSURE]=1;
    prefs.choice[BOOST_COOLANT_ALERT]=1;prefs.choice[BOOST_OIL_PRESSURE_ALERT]=1;
    assert(prefs.save(kPreferences));
    bmw::IDispatcher dispatcher;bmw::Bundle bundle;bmw::RHMIInterfaceVersion version={1};
    BoostDeck app(dispatcher,bmw::BasicString<char>("BoostDeck"),1,0,version,bundle,bundle);
    assert(app.onInit());
    assert(app.texts[360]=="Engine profile: N57");
    assert(app.texts[123]=="Gauge style: Circular dials");
    assert(app.testState(100,11,23,1));tick(app);assert(collectorLaunches()==0);
    assert(app.testState(100,1,4,1));tick(app);
    assert(collectorLaunches()==1 && (launchedMask()&BD_BIT(BD_REL_TORQUE_DDE)));
    assert(launchedMask()&BD_BIT(BD_ADBLUE));
    assert(launchedMask()&BD_BIT(BD_COOLANT));
    assert(!(launchedMask()&BD_BIT(BD_OIL))); // N57 has no pressure sensor.
    assert(launches.back().size()>=9 && launches.back().back()=="010203");

    app.testAction(504);finishStopped(app);
    assert(!(launchedMask()&BD_BIT(BD_ADBLUE)));
    assert(app.properties[std::make_pair(261u,3u)]==0);
    loadBoostDeckAssignments(kAssignments,initial,diesel,hidden,true);
    assert(diesel && hidden && initial[1][1]==BD_ADBLUE);
    app.testAction(505);finishStopped(app);
    assert(launchedMask()&BD_BIT(BD_ADBLUE));

    assert(app.testState(510,11,23,1));
    app.testAction(600+BD_TORQUE);finishStopped(app);
    assert((launchedMask()&BD_BIT(BD_TORQUE)) && !(launchedMask()&BD_BIT(BD_REL_TORQUE_DDE)));
    assert(app.testState(510,11,23,0));

    fail_assignments=true;
    assert(app.testState(510,11,23,1));app.testAction(600+BD_REL_TORQUE_DDE);tick(app);
    assert(!(launchedMask()&BD_BIT(BD_REL_TORQUE_DDE)));
    fail_assignments=false;
    assert(app.testState(100,1,4,0));finishStopped(app);
    const unsigned stopped=collectorLaunches();
    fixture_now+=10000;tick(app);assert(collectorLaunches()==stopped);
    assert(activeCollectors()==0);
    app.onFinalize();
    unlink(storagePath(kAssignments).c_str());unlink(storagePath(kPreferences).c_str());
    assert(rmdir(directory)==0);
    puts("BoostDeck upstream single panel: N57 selectors, masks, dials/settings, emissions and focus stop OK");
}
