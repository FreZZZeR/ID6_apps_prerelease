#include "boostdeck_assignments.h"
#include "n57_gauge_support.h"
#include <assert.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>

int main() {
    assert(n57_gauge_supported(BD_RPM));
    assert(n57_gauge_supported(BD_TORQUE));
    assert(n57_gauge_supported(BD_POWER));
    assert(n57_gauge_supported(BD_TRANS)); // available on HSFZ; MOST excludes EGS separately
    assert(n57_gauge_supported(BD_FUEL_VOLUME));
    assert(!n57_gauge_supported(BD_LOAD));
    assert(!n57_gauge_supported(BD_AFR));
    assert(!n57_gauge_supported(BD_OIL));
    assert(!n57_gauge_supported(BD_COUNT));
    char directory[]="/tmp/id6-n57-availability-XXXXXX";
    assert(mkdtemp(directory));
    char path[256];
    snprintf(path,sizeof path,"%s/assignments",directory);
    unsigned char choices[2][kBoostDeckSlots];
    bool diesel, hidden;
    loadBoostDeckAssignments(path,choices,diesel,hidden,false);
    assert(choices[1][1]==BD_LOAD);
    assert(boostDeckSelectionMask(choices[1],true,false)&BD_BIT(BD_LOAD));
    assert(saveBoostDeckAssignments(path,choices,true,false));
    loadBoostDeckAssignments(path,choices,diesel,hidden,true);
    assert(diesel && !hidden && choices[1][1]==BD_TORQUE);
    assert(boostDeckSelectionMask(choices[1],true,false,true)&BD_BIT(BD_TORQUE));
    assert(!(boostDeckSelectionMask(choices[1],true,false,true)&BD_BIT(BD_LOAD)));
    choices[1][1]=BD_LOAD;
    choices[1][4]=BD_AFR; // retain a custom saved selection without requesting unsupported DIDs
    assert(saveBoostDeckAssignments(path,choices,true,false));
    loadBoostDeckAssignments(path,choices,diesel,hidden,true);
    assert(choices[1][1]==BD_LOAD && choices[1][4]==BD_AFR);
    assert(boostDeckSignalHidden(BD_LOAD,true,false,true));
    assert(!boostDeckSignalHidden(BD_LOAD,true,false,false));
    assert(!boostDeckSignalHidden(BD_LOAD,false,false,true));
    bd_mask mask=boostDeckSelectionMask(choices[1],true,false,true);
    assert(!(mask&BD_BIT(BD_LOAD)) && !(mask&BD_BIT(BD_AFR)));
    choices[1][1]=BD_POWER;
    assert(boostDeckSelectionMask(choices[1],true,false,true)&BD_BIT(BD_POWER));
    assert(!boostDeckSignalHidden(BD_TORQUE,true,false,true));
    assert(boostDeckSignalHidden(BD_ADBLUE,true,true,true));
    assert(unlink(path)==0 && rmdir(directory)==0);
    puts("N57 available-channel selection and legacy-default migration passed");
}
