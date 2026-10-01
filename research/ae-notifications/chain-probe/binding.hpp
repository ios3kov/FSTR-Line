#pragma once
#include "chain_abi.hpp"
namespace fstr::research {
struct Binding { Insert insert=nullptr; Remove remove=nullptr; };
// Does not load an absent Adobe library or call its code. Keeps successful image
// handles pinned for the process lifetime. No generic path/symbol override.
bool bind_loaded_ae(Binding& binding, const char*& reason) noexcept;
bool on_main_thread() noexcept;
bool pin_probe_module() noexcept;
} // namespace fstr::research
