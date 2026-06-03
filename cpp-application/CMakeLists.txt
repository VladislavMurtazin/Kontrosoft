cmake_minimum_required(VERSION 3.14)
project(grpc_udp_monitor LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(gRPC CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)
find_package(Boost REQUIRED COMPONENTS system)

set(PROTO_FILE "${CMAKE_CURRENT_SOURCE_DIR}/monitor.proto")
set(PROTO_GEN_DIR "${CMAKE_CURRENT_BINARY_DIR}")

add_custom_command(
    OUTPUT ${PROTO_GEN_DIR}/monitor.pb.cc ${PROTO_GEN_DIR}/monitor.pb.h
           ${PROTO_GEN_DIR}/monitor.grpc.pb.cc ${PROTO_GEN_DIR}/monitor.grpc.pb.h
    COMMAND ${Protobuf_PROTOC_EXECUTABLE}
        ARGS --grpc_out=${PROTO_GEN_DIR}
             --cpp_out=${PROTO_GEN_DIR}
             -I ${CMAKE_CURRENT_SOURCE_DIR}
             --plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>
             ${PROTO_FILE}
    DEPENDS ${PROTO_FILE}
    COMMENT "Generating protobuf/gRPC stubs"
)

add_executable(grpc_udp_monitor
    main.cpp
    ${PROTO_GEN_DIR}/monitor.pb.cc
    ${PROTO_GEN_DIR}/monitor.grpc.pb.cc
)

target_include_directories(grpc_udp_monitor PRIVATE ${PROTO_GEN_DIR})
target_link_libraries(grpc_udp_monitor PRIVATE
    gRPC::grpc++
    protobuf::libprotobuf
    Boost::system
)