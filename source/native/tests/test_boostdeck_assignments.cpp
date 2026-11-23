#include "boostdeck_assignments.h"
#include <assert.h>

static void writeFile(const char* path, const unsigned char* data, size_t length) {
    FILE* f=fopen(path,"wb");
    assert(f && fwrite(data,1,length,f)==length);
    assert(!fclose(f));
}

int main() {
    char path[]="/tmp/boostdeck-assignments-XXXXXX";
    int fd=mkstemp(path);
    assert(fd>=0); close(fd); unlink(path);
    unsigned char signals[2][kBoostDeckSlots], saved[2][kBoostDeckSlots];
    bool diesel=true, hidden=true;
    loadBoostDeckAssignments(path,signals,diesel,hidden);
    assert(!diesel && !hidden && signals[0][0]==BD_BOOST && signals[1][2]==BD_RPM);
    const unsigned char selected[kBoostDeckSlots]={BD_ADBLUE, BD_DPF_SOOT, BD_DPF_DP,
        BD_DPF_REGEN_DIST, BD_EGT_PRE_DPF, BD_EGT_PRE_CAT, BD_RPM, BD_TORQUE, BD_POWER};
    memcpy(signals[1],selected,sizeof selected);
    memcpy(saved,signals,sizeof saved);
    assert(saveBoostDeckAssignments(path,signals,true,true));
    memset(signals,0,sizeof signals);
    loadBoostDeckAssignments(path,signals,diesel,hidden);
    assert(diesel && hidden && !memcmp(signals,saved,sizeof saved));
    bd_mask stock=0;
    for (unsigned i=0;i<kBoostDeckSlots;++i) stock|=BD_BIT(selected[i]);
    const bd_mask removed=BD_BIT(BD_ADBLUE)|BD_BIT(BD_DPF_SOOT)|BD_BIT(BD_DPF_DP)|BD_BIT(BD_DPF_REGEN_DIST);
    assert(boostDeckSelectionMask(signals[1],diesel,hidden)==(stock & ~removed));
    assert(!boostDeckSignalHidden(BD_EGT_PRE_DPF,diesel,hidden));
    assert(!boostDeckSignalHidden(BD_EGT_PRE_CAT,diesel,hidden));
    assert(boostDeckSelectionMask(signals[1],true,false)==stock);
    assert(boostDeckSelectionMask(signals[1],false,true)==stock);
    unsigned char allHidden[kBoostDeckSlots]; memset(allHidden,BD_ADBLUE,sizeof allHidden);
    assert(boostDeckSelectionMask(allHidden,true,true)==0);
    assert(saveBoostDeckAssignments(path,signals,diesel,false));
    loadBoostDeckAssignments(path,signals,diesel,hidden);
    assert(!hidden && !memcmp(signals,saved,sizeof saved));

    // Existing B1/B2 profiles keep assignments and show all stock channels.
    unsigned char v2[3+sizeof signals]={'B',2,1};
    memcpy(v2+3,saved,sizeof saved); writeFile(path,v2,sizeof v2);
    loadBoostDeckAssignments(path,signals,diesel,hidden);
    assert(diesel && !hidden && !memcmp(signals,saved,sizeof saved));
    unsigned char v1[25]={'B',1,1};
    memcpy(v1+3,saved[0],kBoostDeckSlots); memcpy(v1+14,saved[1],kBoostDeckSlots);
    writeFile(path,v1,sizeof v1); loadBoostDeckAssignments(path,signals,diesel,hidden);
    assert(diesel && !hidden && !memcmp(signals,saved,sizeof saved));

    unsigned char corrupt[4+sizeof signals+1]={'B',3,1,1};
    memcpy(corrupt+4,saved,sizeof saved);
    const size_t bytes=sizeof corrupt-1;
    for (unsigned kind=0;kind<7;++kind) {
        unsigned char data[sizeof corrupt]; memcpy(data,corrupt,sizeof data);
        size_t length=bytes;
        if (kind==0) data[0]='X';
        if (kind==1) data[1]=4;
        if (kind==2) data[2]=2;
        if (kind==3) data[3]=2;
        if (kind==4) data[4]=BD_COUNT;
        if (kind==5) --length;
        if (kind==6) ++length;
        writeFile(path,data,length); loadBoostDeckAssignments(path,signals,diesel,hidden);
        assert(!diesel && !hidden && signals[1][2]==BD_RPM);
    }
    unlink(path);
    assert(!saveBoostDeckAssignments("/no-such-directory/BoostDeck.signals",saved,true,true));
    puts("BoostDeck: persisted visibility, stock defaults, B1/B2 migration, masks and corrupt settings OK");
    return 0;
}
