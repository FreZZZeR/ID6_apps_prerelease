#ifndef BOOSTDECK_ASSIGNMENTS_H
#define BOOSTDECK_ASSIGNMENTS_H
#include "gauge_core.h"
#include "gauge_preferences.h"
#include <string.h>

enum { kBoostDeckSlots = 9 };

inline bool boostDeckEmissionsSignal(unsigned signal) {
    return signal==BD_ADBLUE || signal==BD_DPF_SOOT || signal==BD_DPF_DP || signal==BD_DPF_REGEN_DIST;
}

inline bool boostDeckSignalHidden(unsigned signal, bool diesel, bool hideEmissions) {
    return diesel && hideEmissions && boostDeckEmissionsSignal(signal);
}

inline bd_mask boostDeckSelectionMask(const unsigned char* signals, bool diesel, bool hideEmissions) {
    bd_mask mask=0;
    for (unsigned i=0;i<kBoostDeckSlots;++i)
        if (!boostDeckSignalHidden(signals[i],diesel,hideEmissions)) mask|=BD_BIT(signals[i]);
    return mask;
}

inline void loadBoostDeckAssignments(const char* path, unsigned char (&signals)[2][kBoostDeckSlots],
                                      bool& diesel, bool& hideEmissions) {
    static const unsigned char dieselDefaults[kBoostDeckSlots]={
        BD_BOOST, BD_LOAD, BD_RPM, BD_IAT, BD_TRANS, BD_RAIL, BD_MAF, BD_COOLANT, BD_MAP
    };
    diesel=hideEmissions=false;
    for (unsigned i=0;i<kBoostDeckSlots;++i) signals[0][i]=static_cast<unsigned char>(i);
    memcpy(signals[1],dieselDefaults,sizeof dieselDefaults);
    FILE* file=fopen(path,"rb");
    if (!file) return;
    const unsigned previousSlots=11;
    unsigned char data[3+2*previousSlots];
    const size_t length=fread(data,1,sizeof data,file);
    const bool complete=fgetc(file)==EOF && !ferror(file);
    fclose(file);
    if (!complete || length<3 || data[0]!='B' || data[2]>1) return;
    unsigned stride=0, offset=3;
    if (data[1]==1 && length==3+2*previousSlots) stride=previousSlots;
    if (data[1]==2 && length==3+sizeof signals) stride=kBoostDeckSlots;
    if (data[1]==3 && length==4+sizeof signals && data[3]<=1) {
        stride=kBoostDeckSlots; offset=4;
    }
    if (!stride) return;
    for (unsigned profile=0;profile<2;++profile)
        for (unsigned i=0;i<kBoostDeckSlots;++i)
            if (data[offset+profile*stride+i]>=BD_COUNT) return;
    diesel=data[2]!=0;
    hideEmissions=offset==4 && data[3]!=0;
    for (unsigned profile=0;profile<2;++profile)
        memcpy(signals[profile],data+offset+profile*stride,kBoostDeckSlots);
}

inline bool saveBoostDeckAssignments(const char* path, const unsigned char (&signals)[2][kBoostDeckSlots],
                                      bool diesel, bool hideEmissions) {
    unsigned char data[4+sizeof signals]={'B',3,static_cast<unsigned char>(diesel),
                                       static_cast<unsigned char>(hideEmissions)};
    memcpy(data+4,signals,sizeof signals);
    return savePersistentBytes(path,data,sizeof data);
}
#endif
