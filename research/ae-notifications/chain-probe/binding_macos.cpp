#include "binding.hpp"
#include <CoreFoundation/CoreFoundation.h>
#include <CommonCrypto/CommonDigest.h>
#include <mach-o/loader.h>
#include <mach-o/fat.h>
#include <dlfcn.h>
#include <pthread.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <array>
#include <cstring>
#include <limits.h>
#include <stdexcept>
#include <string>
#include <vector>

namespace fstr::research {
namespace {
struct Image {
    const char *path, *hash, *uuid, *anchor;
};
constexpr Image images[] = {
    {"Contents/Frameworks/BEE.dylib",
     "817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca",
     "161300f373f83ebca751959df40a073b", insert_symbol},
    {"Contents/Frameworks/AfterFXLib.framework/Versions/A/AfterFXLib",
     "ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a",
     "edc800d69e4b3a039bbb8239f3f6eea5", "_ZN7CEggApp11BirthSuitesEv"}
};
std::string hex(const unsigned char* bytes, size_t n) {
    constexpr char digits[]="0123456789abcdef";
    std::string s; s.reserve(2*n);
    for (size_t i=0;i<n;++i) { s+=digits[bytes[i]>>4]; s+=digits[bytes[i]&15]; }
    return s;
}
void require(bool valid) { if (!valid) throw std::runtime_error("image mismatch"); }
bool value_is(CFBundleRef bundle, CFStringRef key, CFStringRef expected) {
    auto value=CFBundleGetValueForInfoDictionaryKey(bundle,key);
    return value && CFGetTypeID(value)==CFStringGetTypeID() && CFEqual(value,expected);
}
std::string canonical(const char* path) {
    char buf[PATH_MAX]; require(realpath(path,buf)!=nullptr); return buf;
}
std::vector<unsigned char> read_file(const std::string& path) {
    const int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK);
    require(fd>=0);
    struct Close {int fd; ~Close(){close(fd);}} close_fd{fd};
    struct stat st{}; require(fstat(fd,&st)==0 && S_ISREG(st.st_mode) &&
                            st.st_size>0 && st.st_size<128*1024*1024);
    std::vector<unsigned char> data(static_cast<size_t>(st.st_size));
    size_t off=0;
    while(off<data.size()) { const auto n=pread(fd,data.data()+off,data.size()-off,off);
                            require(n>0); off+=static_cast<size_t>(n); }
    struct stat after{}; require(fstat(fd,&after)==0 && after.st_size==st.st_size &&
        after.st_mtimespec.tv_sec==st.st_mtimespec.tv_sec &&
        after.st_mtimespec.tv_nsec==st.st_mtimespec.tv_nsec);
    return data;
}
uint32_t be32(const unsigned char* p) {
    return uint32_t(p[0])<<24|uint32_t(p[1])<<16|uint32_t(p[2])<<8|p[3];
}
// This input has already passed the pinned whole-file SHA. Only thin arm64 and
// the observed fat32 container are accepted; other formats fail closed.
size_t slice_offset(const std::vector<unsigned char>& data) {
    require(data.size()>=sizeof(mach_header_64));
    uint32_t magic; memcpy(&magic,data.data(),4);
    if(magic==MH_MAGIC_64) return 0;
    require(be32(data.data())==FAT_MAGIC);
    const auto count=be32(data.data()+4); require(count>0 && count<=32 && 8+20*count<=data.size());
    size_t found=0, offset=0;
    for(uint32_t i=0;i<count;++i) {
        const auto p=data.data()+8+20*i;
        if(be32(p)==CPU_TYPE_ARM64 && be32(p+4)==CPU_SUBTYPE_ARM64_ALL) {
            offset=be32(p+8); const auto size=be32(p+12);
            require(offset<=data.size() && size<=data.size()-offset && size>=sizeof(mach_header_64));
            ++found;
        }
    }
    require(found==1); return offset;
}
void* verified_image(const std::string& root, const Image& expected) {
    const std::string path=canonical((root+"/"+expected.path).c_str());
    require(path.compare(0,root.size()+1,root+"/")==0);
    void* handle=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL|RTLD_NOLOAD|RTLD_FIRST);
    require(handle!=nullptr);
    struct Guard {void* h; ~Guard(){if(h)dlclose(h);}} guard{handle};
    void* symbol=dlsym(handle,expected.anchor); require(symbol!=nullptr);
    Dl_info info{}; require(dladdr(symbol,&info)!=0 && info.dli_fbase && info.dli_fname);
    require(canonical(info.dli_fname)==path);
    const auto data=read_file(path);
    unsigned char hash[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256(data.data(),static_cast<CC_LONG>(data.size()),hash);
    require(hex(hash,sizeof(hash))==expected.hash);
    const size_t slice=slice_offset(data);
    const auto* disk=reinterpret_cast<const mach_header_64*>(data.data()+slice);
    const auto* loaded=static_cast<const mach_header_64*>(info.dli_fbase);
    require(disk->magic==MH_MAGIC_64 && loaded->magic==MH_MAGIC_64 &&
            loaded->cputype==CPU_TYPE_ARM64 && loaded->cpusubtype==CPU_SUBTYPE_ARM64_ALL &&
            memcmp(disk,loaded,sizeof(*disk))==0);
    require(disk->sizeofcmds<=1024*1024 && disk->sizeofcmds<=data.size()-slice-sizeof(*disk));
    const auto* cmds=reinterpret_cast<const unsigned char*>(disk+1);
    require(memcmp(cmds,loaded+1,disk->sizeofcmds)==0);
    size_t off=0, uuid_count=0, text_count=0;
    for(uint32_t i=0;i<disk->ncmds;++i) {
        require(off+sizeof(load_command)<=disk->sizeofcmds);
        const auto* cmd=reinterpret_cast<const load_command*>(cmds+off);
        require(cmd->cmdsize>=8 && cmd->cmdsize<=disk->sizeofcmds-off);
        if(cmd->cmd==LC_UUID) {
            require(cmd->cmdsize==sizeof(uuid_command));
            require(hex(reinterpret_cast<const uuid_command*>(cmd)->uuid,16)==expected.uuid); ++uuid_count;
        }
        if(cmd->cmd==LC_SEGMENT_64) {
            require(cmd->cmdsize>=sizeof(segment_command_64));
            const auto* seg=reinterpret_cast<const segment_command_64*>(cmd);
            require(seg->nsects<4096 && sizeof(*seg)+seg->nsects*sizeof(section_64)<=cmd->cmdsize);
            if(strncmp(seg->segname,"__TEXT",16)==0 && seg->fileoff==0) {
                const auto* sections=reinterpret_cast<const section_64*>(seg+1);
                for(uint32_t j=0;j<seg->nsects;++j) if(strncmp(sections[j].sectname,"__text",16)==0) {
                    const auto& s=sections[j]; require(s.addr>=seg->vmaddr && s.size>0 &&
                        s.addr-seg->vmaddr<=seg->vmsize && s.size<=seg->vmsize-(s.addr-seg->vmaddr) &&
                        s.offset<=data.size()-slice && s.size<=data.size()-slice-s.offset);
                    const auto* memory=static_cast<const unsigned char*>(info.dli_fbase)+(s.addr-seg->vmaddr);
                    require(memcmp(memory,data.data()+slice+s.offset,s.size)==0); ++text_count;
                }
            }
        }
        off+=cmd->cmdsize;
    }
    require(off==disk->sizeofcmds && uuid_count==1 && text_count==1);
    guard.h=nullptr; return handle; // bounded resident pin, not unloaded under callbacks
}
}
bool on_main_thread() noexcept {return pthread_main_np()!=0;}
bool pin_probe_module() noexcept {
    Dl_info info{};
    return dladdr(reinterpret_cast<void*>(&pin_probe_module),&info)!=0 && info.dli_fname &&
        dlopen(info.dli_fname,RTLD_NOW|RTLD_NOLOAD|RTLD_NODELETE)!=nullptr;
}
bool bind_loaded_ae(Binding& out, const char*& reason) noexcept {
    out={}; reason="HOST_IDENTITY_REFUSED";
#if !defined(__arm64__) || defined(__arm64e__)
    return false;
#else
    struct Pins { void* bee=nullptr; void* ui=nullptr;
        ~Pins(){if(ui)dlclose(ui);if(bee)dlclose(bee);} } pins;
    try {
        require(on_main_thread());
        const auto bundle=CFBundleGetMainBundle(); require(bundle!=nullptr);
        require(value_is(bundle,kCFBundleIdentifierKey,CFSTR("com.adobe.AfterEffects.application")) &&
                value_is(bundle,CFSTR("CFBundleShortVersionString"),CFSTR("25.6.0")) &&
                value_is(bundle,kCFBundleVersionKey,CFSTR("25.6.0.101")));
        const auto url=CFBundleCopyBundleURL(bundle); require(url!=nullptr);
        unsigned char path[PATH_MAX]; const bool got=CFURLGetFileSystemRepresentation(url,true,path,sizeof(path));
        CFRelease(url); require(got);
        const auto root=canonical(reinterpret_cast<const char*>(path));
        void* bee=verified_image(root,images[0]); pins.bee=bee;
        pins.ui=verified_image(root,images[1]);
        void* insert=dlsym(bee,insert_symbol); void* remove=dlsym(bee,remove_symbol);
        require(insert && remove);
        Dl_info a{},b{}; require(dladdr(insert,&a) && dladdr(remove,&b) && a.dli_fbase==b.dli_fbase);
        memcpy(&out.insert,&insert,sizeof(insert)); memcpy(&out.remove,&remove,sizeof(remove));
        pins.bee=pins.ui=nullptr; // AEGP owner retains one successful binding for this process
        reason="EXACT_IMAGES_VERIFIED_NOT_RUNTIME_ACCEPTANCE"; return true;
    } catch(...) {out={}; return false;}
#endif
}
} // namespace fstr::research
