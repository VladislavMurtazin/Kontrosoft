#include <iostream>
#include <thread>
#include <atomic>
#include <vector>
#include <csignal>

#include <boost/asio.hpp>

#include <grpcpp/grpcpp.h>
#include "monitor.grpc.pb.h"

using grpc::ServerContext;
using grpc::Status;
using monitor::Empty;
using monitor::BoolResponse;
using monitor::UdpStats;
using monitor::MonitorService;

// ================== gRPC SERVICE ==================
class MonitorServiceImpl final : public MonitorService::Service {
public:
    MonitorServiceImpl(std::atomic<bool>& ready,
                       std::atomic<uint8_t>& pkts,
                       std::atomic<uint8_t>& aBytes)
        : ready_(ready), pkts_(pkts), aBytes_(aBytes) {}

    Status IsReady(ServerContext*, const Empty*, BoolResponse* response) override {
        response->set_is_ready(ready_.load());
        return Status::OK;
    }

    Status GetUdpStatistics(ServerContext*, const Empty*, UdpStats* response) override {
        response->set_packets(pkts_.load());
        response->set_abytes(aBytes_.load());
        return Status::OK;
    }

private:
    std::atomic<bool>& ready_;
    std::atomic<uint8_t>& pkts_;
    std::atomic<uint8_t>& aBytes_;
};

// ================== UDP LISTENER ==================
class UdpListener {
public:
    UdpListener(boost::asio::io_context& io, uint16_t port,
                std::atomic<uint8_t>& pkts, std::atomic<uint8_t>& aBytes)
        : socket_(io, boost::asio::ip::udp::endpoint(
              boost::asio::ip::address::from_string("127.0.0.1"), port)),
          pkts_(pkts), aBytes_(aBytes), buffer_(1500) {
        start_receive();
    }

    void close() { socket_.close(); }

private:
    void start_receive() {
        socket_.async_receive_from(
            boost::asio::buffer(buffer_),
            remote_endpoint_,
            [this](boost::system::error_code ec, std::size_t bytes) {
                if (ec) return; // Остановка или ошибка сети

                pkts_.fetch_add(1);
                uint8_t count_a = 0;
                for (size_t i = 0; i < bytes; ++i) {
                    if (buffer_[i] == 'A') ++count_a;
                }
                aBytes_.fetch_add(count_a);

                start_receive(); // Продолжаем слушать
            });
    }

    boost::asio::ip::udp::socket socket_;
    boost::asio::ip::udp::endpoint remote_endpoint_;
    std::vector<char> buffer_;
    std::atomic<uint8_t>& pkts_;
    std::atomic<uint8_t>& aBytes_;
};

// ================== MAIN ==================
int main() {
    try {
        std::atomic<bool> is_ready{false};
        std::atomic<uint8_t> packet_count{0};
        std::atomic<uint8_t> a_bytes_count{0};

        boost::asio::io_context io_ctx;

        // 1. Поднимаем gRPC сервер
        MonitorServiceImpl service(is_ready, packet_count, a_bytes_count);
        grpc::ServerBuilder builder;
        builder.AddListeningPort("127.0.0.1:2031", grpc::InsecureServerCredentials());
        builder.RegisterService(&service);

        std::unique_ptr<grpc::Server> server = builder.BuildAndStart();
        std::cout << "[INFO] gRPC сервер запущен на 127.0.0.1:2031\n";

        // 2. Открываем прослушивание UDP
        UdpListener udp_listener(io_ctx, 2032, packet_count, a_bytes_count);
        is_ready.store(true);
        std::cout << "[INFO] UDP порт открыт на 127.0.0.1:2032. Система готова.\n";

        // Асинхронная обработка сигналов Linux (SIGINT / SIGTERM)
        boost::asio::signal_set signals(io_ctx, SIGINT, SIGTERM);
        signals.async_wait([&](const boost::system::error_code& ec, int /*signum*/) {
            if (!ec) {
                std::cout << "\n[INFO] Получен сигнал завершения. Graceful shutdown...\n";
                server->Shutdown(); // Корректно останавливает gRPC
                udp_listener.close(); // Закрывает UDP сокет
                io_ctx.stop();        // Останавливает цикл обработки событий
            }
        });

        // Запускаем асинхронный цикл UDP в отдельном потоке
        std::thread udp_thread([&io_ctx]() {
            io_ctx.run();
        });

        // Блокируем главный поток до вызова server->Shutdown()
        server->Wait();

        // Ждем завершения потока UDP
        udp_thread.join();

        std::cout << "[INFO] Приложение завершено с кодом 0.\n";
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "[FATAL] " << e.what() << "\n";
        return 1;
    }
}



