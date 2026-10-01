# After Effects engineering know-how

Общая база переиспользуемых выводов из законченных AE-проектов.

Первый источник: разработка FSTR Stretch / ElasticGridFX 0.9.3, проверенный scope
macOS Apple Silicon / After Effects 2025 25.6. Полная продуктовая ретроспектива:
https://github.com/ios3kov/ElasticGridFX/blob/main/docs/retrospective-0.9.3.md

Этот документ не превращает один успешный проект в универсальную спецификацию AE.
Каждый вывод сохраняет свой scope и evidence.

## Evidence labels

- **PROVEN / VERIFIED** — подтверждено тестами или инструментированным host evidence.
- **USER-REPORTED** — подтверждено пользователем в целевой среде.
- **OBSERVED / RESEARCH** — полезное наблюдение, ещё не полная production-гарантия.
- **FAILED / REJECTED** — подход проверен/проанализирован и отвергнут.
- **UNKNOWN / NOT VERIFIED** — достаточного evidence нет.

## 1. Lifecycle, callbacks и AEGP

### Deferred main-thread work не является синхронной инициализацией

**OBSERVED / RESEARCH; product behavior verified in FSTR Stretch.**

After Effects может запросить frame до того, как deferred idle/main-thread binding
завершился. Нельзя строить render correctness на предположении, что вызов
idle/wakeup уже выполнил нужную работу.

Практический pattern:

- pending-state должен быть явным;
- безопасный neutral/identity fallback допустим только при строгом доказательстве;
- любой non-neutral/invalid pending state должен fail closed;
- render worker не должен сам “доделывать” host binding.

### AEGP/threading boundary должен быть доказан для каждого вызова

**PROVEN engineering constraint.**

Не переносить AEGP mutations в render/MFR worker ради удобства. Host state,
который нужен рендеру, подготавливать в разрешённом lifecycle/main-thread месте и
передавать дальше как immutable snapshot.

### UpdateParamsUi — не скрытый state-mutation hook

**FAILED / REJECTED pattern.**

Использовать callback для UI state/visibility/enabling, а не как неявную
транзакцию записи project data.

## 2. SmartFX / MFR / render state

### PreRender owns dependencies, Render consumes immutable data

**PROVEN / VERIFIED.**

SmartPreRender должен checkout/зафиксировать все значения, от которых зависит
SmartRender. Worker render не читает mutable live parameter arrays.

Это снижает race/reentrancy bugs и делает MFR поведение воспроизводимым.

### Sparse buffer != logical source canvas

**PROVEN / VERIFIED.**

Compact storage rectangle нельзя автоматически считать полным изображением.
Если clamp/edge mode применяется к compact storage, края storage могут размазаться
в логически прозрачную область.

Pattern:

1. вычислять sampling в logical-canvas coordinates;
2. edge behavior применять к logical canvas;
3. затем маппить taps в реально доступный storage;
4. отсутствующие taps трактовать по явному contract, не по случайному краю buffer.

## 3. Coordinates: никогда не смешивать домены

**PROVEN / VERIFIED.**

В AE одновременно могут существовать:

- effect/source canvas coordinates;
- native layer coordinates;
- comp coordinates;
- viewer/frame coordinates;
- normalized plane coordinates;
- raster pixel indices.

Они не взаимозаменяемы.

### W/H boundary и W−1/H−1 raster index — разные вещи

Public point/control boundary может законно использовать W/H, в то время как
последний pixel index — W−1/H−1. Глобальная “поправка на один пиксель” опасна.

Перед coordinate fix сначала назвать домены входа/выхода каждой функции.

### Native text требует отдельной проверки

**PROVEN / VERIFIED on AE 25.6 scope.**

Effect canvas continuously rasterized text может не совпадать с native layer
coordinate semantics. Fixed Position subtraction не является general solution:
rotation, parenting и camera perspective сразу ломают такой shortcut.

### activeCamera не равен “есть camera layer”

**PROVEN / VERIFIED host quirk on AE 25.6.**

В тестовом comp AE возвращал non-null activeCamera без explicit camera layer.
Если тесту важно наличие слоя камеры, проверять topology/layer types, а не только
convenience property.

## 4. Projective / 3D deformation

**PROVEN / VERIFIED in FSTR Stretch scope.**

Для 2D/3D plane deformation полезный общий pattern:

- deformation остаётся в plane-local normalized space;
- projective transform H отвечает за plane ↔ projected space;
- render использует inverse mapping;
- per-frame matrix/homography готовится один раз;
- per-pixel matrix inversion не нужен;
- source sample выполняется один раз;
- render / overlay / hit-test / inverse drag используют одну геометрию.

Conceptually:

`source = H(W^-1(H^-1(q)))`

Сохранять отдельный fast path для непроективного случая.

## 5. Arbitrary data, keyframes, Undo

### UI control density не должна автоматически становиться storage topology

**PROVEN / VERIFIED.**

Если display-only control меняет количество видимых handles, не переписывать из-за
этого animated arbitrary data / keyframes.

Удачный pattern:

- persistent animation state — source of truth;
- visible controls — derived view;
- display change → redraw only;
- только реальный nonzero edit пишет parameter value;
- reentrant UI topology change отменяет текущий drag, а не переназначает его.

### Project-file ABI нужно считать публичным контрактом

Стабильные parameter IDs, order/types и serialized wire schema нельзя менять без
миграционной стратегии. Additive evolution безопаснее rename/reorder.

Unknown future schema лучше явно отвергнуть, чем молча прочитать неверно.

### Undo должен идти через host parameter transaction

Hidden global mutation плохо сочетается с AE Undo/Redo. Пользовательское изменение
должно проходить через штатное parameter value/change semantics и быть проверено в
реальном host.

## 6. Capture и automated AE testing

### Test oracle тоже нужно тестировать

**PROVEN / VERIFIED.**

В FSTR Stretch два раза проблема была не в plugin:

- ExtendScript File metadata сразу после capture могла быть stale;
- `saveFrameToPng` дал 32-bpc darkening независимо от effect.

Вывод: прежде чем объявлять pixel FAIL, доказать корректность capture path.
Для production-like pixel evidence предпочтительнее контролируемый Render Queue
path, если convenience API ведёт себя иначе.

### Owned fixture + fail-closed safety

Каждый destructive/interactive AE test должен:

- доказать ownership fixture/project;
- не закрывать и не перезаписывать чужую dirty работу;
- иметь unique Run ID/output;
- считать timeout/unknown state как BLOCKED;
- удалять только созданное самим тестом;
- не “лечить” FAIL перезапуском или purge без записи причины.

## 7. Build identity и loaded identity

### Installed file != loaded plugin

**PROVEN / VERIFIED.**

AE может иметь user/system plugin copies и уже загруженный image. Проверка файла на
диске не доказывает, какой binary реально исполняется.

Надёжная цепочка:

`source commit → source digest → Build ID → package hash → installed bundle → live loaded image`.

Для native plugin полезны live image UUID/path + PID evidence.

### Evidence нельзя переносить на новый binary

Даже About-only source edit создаёт другой candidate. Старые PASS/hashes нельзя
переименовать в доказательство новой сборки.

## 8. Packaging и macOS distribution

### Version metadata должна иметь один authority

Finder/version fields генерировать из validated build metadata до signing.
Не hardcode version отдельно в packaging script.

### Уже подписанный artifact не мутировать

Rename outer bundle/archive можно делать только способом, который сохраняет
signed payload bytes и modes, с последующей полной проверкой.

### Ad-hoc signing — development only

Публичный macOS product gate:

- Developer ID;
- notarization;
- stapling где применимо;
- codesign/Gatekeeper validation;
- реальный quarantined download/install;
- никаких `xattr`, Open Anyway или Gatekeeper-disable инструкций.

## 9. Legacy Adobe ABI может иметь legacy encoding

**PROVEN / VERIFIED on AE 25.6.**

Не предполагать UTF-8 для старых `A_char`/return-message buffers.
В FSTR Stretch UTF-8 © (`C2 A9`) отобразился как лишний символ + ©; single-byte
`0xA9` дал ожидаемый результат.

Любой non-ASCII product text в legacy ABI проверять в реальном host.

## 10. Cache invalidation

**PROVEN / VERIFIED project lesson.**

После изменения render semantics AE может показывать старый cached frame даже при
правильном новом коде. Для release-level renderer changes нужен сознательный
effect-version/cache invalidation plan, а не ручной purge как пользовательская
инструкция.

## 11. Rejected shortcuts to remember

Не повторять без нового evidence:

- blanket suppression host errors;
- fake ready/initialized markers;
- render-thread AEGP writes;
- polling host initialization из render;
- mutation из UpdateParamsUi;
- fixed Position subtraction для native text;
- activeCamera-null как camera topology proof;
- compact-storage clamp как logical canvas;
- resizing animated state из-за UI density;
- global W/H ↔ W−1/H−1 rewrite;
- “installed means loaded”;
- изменение signed/tested candidate in place;
- hardcoded bundle version;
- convenience capture API как непроверенный pixel oracle;
- security bypass как нормальный macOS install path.

## 12. Default checklist for a new AE project

Перед production implementation:

1. Назвать все coordinate domains.
2. Зафиксировать parameter/project ABI.
3. Зафиксировать lifecycle/threading contract для host API.
4. Определить render snapshot ownership.
5. Создать Build Identity до первых серьёзных host tests.
6. Подготовить test-owned fixture и loaded-identity proof.
7. Для каждой subtle bug сначала создать failing baseline fixture.
8. Проверять production FFI/path, а не только математическую модель.
9. Отделять VERIFIED / USER-REPORTED / RESEARCH / FAILED / UNKNOWN.
10. После milestone переносить reusable выводы сюда и в DEVELOPMENT_RULES при необходимости.

## 13. Scope warning

Эти выводы получены главным образом на After Effects 2025 25.6 / macOS Apple
Silicon. Они являются сильной инженерной базой и проверенными patterns в указанном
scope, но не автоматической сертификацией других версий AE, Windows, Intel,
других Adobe hosts или будущих SDK.
