#pragma once
// Binary-boundary shim, NOT a reconstructed Adobe C++ class.
// Only the supplied AE 25.6.0.101 arm64 contract has been inspected.
// See BEE-CALLBACK-SOURCE-2026-09-30.md. No absolute-address calls or loading.
namespace fstr::research {
using Message = int;
using Result = int;
using Chain = void;
using Callback = Result (*)(Chain*, void* refcon, Message, void* payload);
using Continue = Result (*)(Chain*, Message, void* payload);
using Insert = int (*)(Callback, void* refcon);
using Remove = int (*)(int registration_id);
static_assert(sizeof(Message) == 4 && sizeof(void*) == 8);
static_assert(sizeof(Continue) == sizeof(void*));

// Mach-O nm has an extra leading underscore; dlsym expects these spellings.
inline constexpr const char* insert_symbol =
    "_Z19BEE_Callback_InsertPFiR19BEE_FilterFuncChainI9BEE_CBMsgPvES1_S0_S1_ES1_";
inline constexpr const char* remove_symbol = "_Z19BEE_Callback_Removei";

// PRECONDITION: valid live chain from an independently verified binding.
// Null/unknown chains cannot be 'recovered' by returning 0: that would swallow
// host work. There is deliberately no host binder in this increment.
// No noexcept: downstream C++ exceptions must retain their original unwind.
inline Result continue_chain(Chain* chain, Message message, void* payload) {
    const unsigned char* table = nullptr;
    Continue next = nullptr;
    __builtin_memcpy(&table, chain, sizeof(table));
    __builtin_memcpy(&next, table + 2 * sizeof(void*), sizeof(next));
    return next(chain, message, payload);
}
} // namespace fstr::research
